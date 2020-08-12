'''
One of the challenges in the MATE 2020 Game was to compare two images of a coral reef and detect the health
This script handles aligning them, calculating areas of change, and generating a visual output
It does NOT check to make sure that there are the correct number or type of changes in the coral reef
'''

# Import necessary libraries
import cv2
import numpy as np

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
        raise Exception("The image to overlay is larger than the image it is being overlayed on")

    channels = img.shape[2]

    alpha = alpha_mask # This allows alpha_mask to be a full image [y1o:y2o, x1o:x2o]
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

def findCoralHealth(coral_reference, coral_to_align):
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
    outImages = {
        "backgroundMask": None,
        "features": None,
        "alignment": None,
        "subtraction": None,
        "final": None
    }

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
    outImages["backgroundMask"] = coral_to_align_masked

    # Calculate homography for the reference and target images
    #  * Homography is calculated using the unmasked image, but a mask is passed in to limit feature locations
    coral_matches, h = alignImages(coral_reference, coral_to_align, coral_to_align_mask)
    outImages["features"] = coral_matches

    # Apply homography
    #  * The homography is applied to both the image with and without the mask
    #  * The image with the mask is used in subtraction to calculate differences
    #  * The image without the mask is the image that the rectangles are drawn on
    coral_aligned_mask = cv2.warpPerspective(coral_to_align_masked, h, (width, height))
    coral_aligned = cv2.warpPerspective(coral_to_align, h, (width, height))

    # Overlay the aligned and masked image on the reference image to check alignment
    outImages["alignment"] = overlay_image_alpha(coral_reference, coral_aligned_mask[:, :, 0:3], (0, 0), 0.5)

    # Subtract the two images to find differences in the coral
    #  * The images are converted to float16 from uint8 so they can represent negative numbers
    #    They need to be converted back before they can be used in opencv
    coral_subtracted = cv2.GaussianBlur(coral_reference, blurKSize, blurAmmount).astype("float16") - cv2.GaussianBlur(coral_aligned_mask, blurKSize, blurAmmount).astype("float16")

    # In order to be able to work with negative numbers, a constant, 64, is added to everything
    #  * This affects the color filtering, so if the constant is adjusted, the filters will need be re-tuned
    #  * Finally the image is clipped within range and converted back to uint8
    coral_subtracted = np.clip(np.abs(coral_subtracted+64), 0, 255).astype("uint8")
    outImages["subtraction"] = coral_subtracted


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
    
    outImages["final"] = coral_aligned
    return outImages

'''
Hyperparamters that have been found to work the best for our scenario
'''

# Image alignment parameters
max_features = 10000
good_match_percent = 0.15

# Image size parameters
width = 1920
height = 1080

# Area of change parameters
blurKSize = (5,5)
blurAmmount = 10

min_countour_area = 2000.0

kernel = np.ones((9,9))

expand_amount = 10

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

coral_reference = cv2.imread("coral_7.png")

coral_to_align = cv2.imread("coral_7-difficult.png")

result = findCoralHealth(coral_reference, coral_to_align)

cv2.imshow("coral_to_align_masked", result["backgroundMask"])
cv2.moveWindow("coral_annotated", 1000,50)
cv2.imshow("matches ", result["features"])
cv2.imshow("aligned", result["alignment"])
cv2.imshow("subtraction", result["subtraction"])

cv2.imshow("coral_annotated", result["final"])
cv2.moveWindow("coral_annotated", 1000,50)

cv2.imshow("coral_reference", coral_reference)
cv2.moveWindow("coral_reference", -500,50)

cv2.waitKey(0)
cv2.destroyAllWindows()
