'''
This file has computer vision tools for line following and coral reef health
All of the code is taken from their respective files in Testing/
'''

import cv2
import numpy as np

### LINE FOLLOWING CODE ###

# Line Following Settings
lf_lower_blue = np.array([70,119,87])
lf_upper_blue = np.array([109,255,225])
lf_kernel = np.ones((3,3), np.uint8)
lf_min_countour_area = 7000.0
lf_percent_of_image_blue_lines_should_fill = 0.75 # Equal to (total_width - blue_to_red_dist) / total_width
lf_target_angle = 90.0

def point_slope_line(pt,sl,num,given_axis):
    '''
    Calcualates a where a line intersects an input point

    The line is defined in point slope form (https://www.mathsisfun.com/algebra/line-equation-point-slope.html)
    The input number represents a horizontal or vertical line
    The goal of this function is to calculate where the two lines intersect

    Arguments:
        pt: The point that defines the line
        sl: The slope that defines the line
        num: The x OR y coordinate to intersect the line
        given_axis: Whether num is an x or y value
    
    Returns:
        The coordinate of itersection between the two lines
    '''
    if given_axis == "x":
        return (num, int(sl*(num-pt[0]) + pt[1]))
    elif given_axis == "y":
        return (int((num-pt[1])/sl + pt[0]), num)

def detectLines(img, cvOutLevel=None):
    '''
    Detects two parallel lines in an image, and gets the distance between them and average angle

    Arguments:
        img: The image to detect lines in
        cvOutLevel: What level of debugging to output ("Base", "Mask", "Contours")
    '''
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lf_lower_blue, lf_upper_blue)

    filtered = cv2.erode(mask, lf_kernel, iterations=1)
    filtered = cv2.dilate(filtered, lf_kernel, iterations=15)
    filtered = cv2.erode(filtered, lf_kernel, iterations=9)

    contours, hierarchy = cv2.findContours(filtered, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # This will contain points on each line in the format: start, end, middle, and slope
    lines = []

    if len(contours) >= 2:
        for contour in contours:
            if cv2.contourArea(contour) > lf_min_countour_area:
                # Fit a line to the contour
                vx,vy,x,y = cv2.fitLine(contour, cv2.DIST_L2,0,0.01,0.01)
                vx,vy,x,y = vx[0],vy[0],x[0],y[0]
                slope = vy/vx

                # Calculate where the line intersects the top and bottom of the image
                height = img.shape[1]
                line_top = point_slope_line((x,y),slope,0,"y")
                line_bottom = point_slope_line((x,y), slope, height, "y")

                if cvOutLevel == "Base":
                    # Draw the line on the image
                    cv2.line(img, line_top, line_bottom, (0,0,0) ,5)
                    # Draw the center on the image
                    cv2.line(img,(x,y),(x,y),(0,255,0),10)

                # Append the start, end, middle, and slope of each line to the array
                lines.append([np.array(line_top), np.array(line_bottom), np.array([x,y]), slope])
        
        if len(lines) >= 2:
            # Find the distance between the centers of both lines
            line_dist = np.linalg.norm(lines[0][2]-lines[1][2])

            # Calculate the angle of each line based on it's slope
            line_a_angle = np.degrees(np.arctan(lines[0][3]))
            line_b_angle = np.degrees(np.arctan(lines[1][3]))

            # Fix negative Angles
            if line_a_angle < 0:
                line_a_angle += 180
            if line_b_angle < 0:
                line_b_angle += 180

            # Average the angles for a more accurate result
            avg_angle = (line_a_angle+line_b_angle)/2.0

            # This function will be called on a streaming video, so each run only one debug image needs to be returned
            if cvOutLevel:
                if cvOutLevel == "Base":
                    return line_dist, avg_angle-lf_target_angle, img
                elif cvOutLevel == "Mask":
                    return line_dist, avg_angle-lf_target_angle, filtered
                elif cvOutLevel == "Contours":
                    return line_dist, avg_angle-lf_target_angle, cv2.drawContours(img, contours, -1, (0,255,0), 3)
            else:
                return line_dist, avg_angle-lf_target_angle
    return None

### CORAL HEALTH CODE ###

# Coral Health Settings
changes =  {
    "death": {
        "filters": [
            {
                "lower": (42, 21, 209),
                "upper": (180, 135, 255)
            }
        ],
        "color": (0, 255, 255)
    },
    "growth": {
        "filters": [
            {
                "lower": (53, 78, 62),
                "upper": (78, 255, 163)
            }
        ],
        "color": (0, 255, 0)
    },
    "bleached": {
        "filters": [
            {
                "lower": (0, 147, 0),
                "upper": (33, 255, 137)
            },
            {
                "lower": (159, 147, 0),
                "upper": (180, 255, 137)
            }
        ],
        "color": (0, 0, 255)
    },
    "healed": {
        "filters": [
            {
                "lower": (66, 101, 163),
                "upper": (115, 255, 255)
            }
        ],
        "color": (255, 0, 0)
    }
}

background_mask = {
    "bleached": {
        "lower": (73, 0, 133),
        "upper": (112, 98, 255)
    },
    "healthy": {
        "lower": (117, 55, 112),
        "upper": (180, 255, 255)
    }
}

# Image alignment settings
max_features = 10000
good_match_percent = 0.15

# Image size settings
width = 1920
height = 1080

# Image subtraction/blur settings
blurKSize = (5,5)
blurAmmount = 10

# Image countouring settings
min_countour_area = 2000.0

# Mask smoothing kernel
kernel = np.ones((9,9))

# Box expansion amount
expand_amount = 10

# Coral image reference
coral_reference_path = "static/assets/coralHealth/coral_old.png"

# Coral Health Helper functions

def overlay_image_alpha(img, img_overlay, pos, alpha_mask):
    '''
    Overlay one image ontop of another given an imput transparency mask

    Arguments:
        img: The base image
        img_overlay: The image to overlay (should be smaller than img)
        pos: the location of to overlay img_overlay
        alpha_mask: the alpha of the overlay images

    Returns:
        The new image with the overlay appled
    '''
    img = img.copy()

    x, y = pos

    # Image ranges
    y1, y2 = max(0, y), min(img.shape[0], y + img_overlay.shape[0])
    x1, x2 = max(0, x), min(img.shape[1], x + img_overlay.shape[1])

    # Overlay ranges
    y1o, y2o = max(0, -y), min(img_overlay.shape[0], img.shape[0] - y)
    x1o, x2o = max(0, -x), min(img_overlay.shape[1], img.shape[1] - x)

    # Exit if nothing to do
    if y1 >= y2 or x1 >= x2 or y1o >= y2o or x1o >= x2o:
        return

    channels = img.shape[2]

    alpha = alpha_mask #This allows alpha_mask to be a full image [y1o:y2o, x1o:x2o]
    alpha_inv = 1.0 - alpha

    for c in range(channels):
        img[y1:y2, x1:x2, c] = (alpha * img_overlay[y1o:y2o, x1o:x2o, c] +
                                alpha_inv * img[y1:y2, x1:x2, c])
    return img

def alignImages(reference, toAlign, toAlignMask):
    '''
    Aligns two images using ORB features

    Arguments:
        reference: The reference image to align to
        toAlign: The image that is being aligned
        toAlignMask: A mask for toAlign to specifiy what parts of it should be used in alignment calculations

    Returns:
        An image with the matched features marked
        A homography matrix that can be used to align the images
    '''
    # Convert images to grayscale
    im1Gray = cv2.cvtColor(toAlign, cv2.COLOR_BGR2GRAY)
    im2Gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    # Detect ORB features and compute descriptors.
    detector = cv2.ORB_create(max_features)
    keypoints1, descriptors1 = detector.detectAndCompute(im1Gray, mask=toAlignMask)
    keypoints2, descriptors2 = detector.detectAndCompute(im2Gray, mask=None)

    # Match features.
    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.match(descriptors1, descriptors2, None)

    # Sort matches by score
    matches.sort(key=lambda x: x.distance, reverse=False)

    # Remove not so good matches
    numGoodMatches = int(len(matches) * good_match_percent)
    matches = matches[:numGoodMatches]

    # Draw top matches
    imMatches = cv2.drawMatches(toAlign, keypoints1, reference, keypoints2, matches, None)

    # Extract location of good matches
    points1 = np.zeros((len(matches), 2), dtype=np.float32)
    points2 = np.zeros((len(matches), 2), dtype=np.float32)
 
    for i, match in enumerate(matches):
        points1[i, :] = keypoints1[match.queryIdx].pt
        points2[i, :] = keypoints2[match.trainIdx].pt
   
    # Find homography
    h, mask = cv2.findHomography(points1, points2, cv2.RANSAC)
    
    return imMatches, h 

def HSVThreshold(img, lower, upper):
    '''
    Applies a HSV threshold to a BGR image

    Arguments:
        img: The image to threshold
        lower: The lower HSV bound
        upper: The upper HSV bound
    
    Returns:
        The thresholded image in the form of a mask
    '''
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    return mask

def smoothImage(img, dilate, erode):
    '''
    Smoothes a mask using dilation and erosion (dilation is applied before erosion)

    Arguments:
        img: The mask to smooth
        dilate: The amount to dilate
        erode: The amount to erode
    
    Returns:
        The smoothed image
    '''
    smoothed = cv2.dilate(img, kernel, dilate)
    smoothed = cv2.erode(smoothed, kernel, erode)
    return smoothed

# Coral Health Main Function

def findCoralHealth(coral_to_align, cvOutPath, done=None):
    '''
    Finds the change health of a coral reef by comparing two images of it

    Arguments:
        coral_reference: The reference image of the coral reef (This will be provided by MATE)
        coral_to_align: The target image to compare against the reference (This will likely come from our camera)
    
    Returns:
        A dictionary containing several images:
            backgroundMask: The target image with the background removed (used to evaluate the background removal)
            features: A mapping of image alignment features between the reference and target images (used to evaluate image alignment)
            alignment: The reference image overlayed with the aligned target image (used to evaluate alignment)
            subtraction: The change in color between the reference and target images (used to evaluate detection of areas of change)
            final: The target image with all areas of change marked in their respective colors
    '''
    coral_reference = cv2.imread(coral_reference_path)
    cv2.imwrite(cvOutPath+"input.png", coral_to_align)

    # Generate a background mask for the coral to be aligned
    #  * The coral reef has two colors, pink (healthy) and white (bleached), so two separate masks are combined for greater accuracy
    coral_to_align_mask = (HSVThreshold(coral_to_align, background_mask["bleached"]["lower"], background_mask["bleached"]["upper"]) +
                           HSVThreshold(coral_to_align, background_mask["healthy"]["lower"], background_mask["healthy"]["upper"]))

    # Smooth the mask
    coral_to_align_mask = cv2.erode(coral_to_align_mask, kernel, 1)
    coral_to_align_mask = cv2.dilate(coral_to_align_mask, kernel, 10)
    coral_to_align_mask = cv2.dilate(coral_to_align_mask, kernel, 1)

    # Apply the mask
    coral_to_align_masked = cv2.bitwise_and(coral_to_align, coral_to_align, mask=coral_to_align_mask)
    cv2.imwrite(cvOutPath+"background_mask.png", coral_to_align_masked)

    # Calculate homography for the reference and target images
    #  * Homography is calculated using the unmasked image, but a mask is passed in to limit feature locations
    coral_matches, h = alignImages(coral_reference, coral_to_align, coral_to_align_mask)
    cv2.imwrite(cvOutPath+"features.png", coral_matches)

    # Apply homography
    #  * The homography is applied to both the image with and without the mask
    #  * The image with the mask is used in subtraction to calculate differences
    #  * The image without the mask is the image that the rectangles are drawn on
    coral_aligned_mask = cv2.warpPerspective(coral_to_align_masked, h, (width, height))
    coral_aligned = cv2.warpPerspective(coral_to_align, h, (width, height))

    # Overlay the aligned and masked image on the reference image to check alignment
    cv2.imwrite(cvOutPath+"alignment.png", overlay_image_alpha(coral_reference, coral_aligned_mask[:, :, 0:3], (0, 0), 0.5))

    # Subtract the two images to find differences in the coral
    #  * The images are converted to float16 from uint8 so they can represent negative numbers
    #    They need to be converted back before they can be used in opencv
    coral_subtracted = cv2.GaussianBlur(coral_reference, blurKSize, blurAmmount).astype("float16") - cv2.GaussianBlur(coral_aligned_mask, blurKSize, blurAmmount).astype("float16")
    outImages["subtraction"] = coral_subtracted
    cv2.imwrite("subtraction.png", coral_subtracted)

    # In order to be able to work with negative numbers, a constant, 64, is added to everything
    #  * This affects the color filtering, so if the constant is adjusted, the filters will need be re-tuned
    #  * Finally the image is clipped within range and converted back to uint8
    coral_subtracted = np.clip(np.abs(coral_subtracted+64), 0, 255).astype("uint8")


    # Mark Changes on the reef
    #  * This is done by looping through each of the 4 kinds of change
    #    Applying the corresponding color filter, and looking for large contours
    for key in changes:
        # Each type of change will have at least one color filter
        mask = HSVThreshold(coral_subtracted, changes[key]["filters"][0]["lower"], changes[key]["filters"][0]["upper"])

        # Because red's hue is ~0 and ~180, some types of change will have more than one filter
        #  * This loops through any additional filters and adds them
        if len(changes[key]["filters"]) > 1:
            for colorFilter in changes[key]["filters"]:
                mask += HSVThreshold(coral_subtracted, colorFilter["lower"], colorFilter["upper"])
        
        # Smooth the mask
        mask_smooth = cv2.erode(mask, kernel, 1)
        mask_smooth = cv2.dilate(mask_smooth, kernel, 1)
        mask_smooth = cv2.dilate(mask_smooth, kernel, 1)

        # Calculate contours
        contours, hierarchy = cv2.findContours(mask_smooth, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Loop through each contour, filtering out the small ones
        # Draw boxes of the corresponding color
        for contour in contours:
            if cv2.contourArea(contour) > min_countour_area:
                (x,y,w,h) = cv2.boundingRect(contour)
                x -= expand_amount
                y -= expand_amount
                w += expand_amount*2
                h += expand_amount*2
                cv2.rectangle(coral_aligned, (x,y), (x+w,y+h), changes[key]["color"], 2)
    
    cv2.imwrite("final.png", coral_aligned)

    # If this is run in a thread, the user can specify a place
    # to store the out put without returning it
    done = True

    return outImages