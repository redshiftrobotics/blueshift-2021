import cv2
import numpy as np

MAX_FEATURES = 1000
GOOD_MATCH_PERCENT = 0.15
 
def cropImage(img, x1,y1,x2,y2):
    return img[y1:y2, x1:x2]

def overlay_image_alpha(img, img_overlay, pos, alpha):
    """Overlay img_overlay on top of img at the position specified by
    pos and blend using alpha.
    """

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

    alpha_inv = 1.0 - alpha

    for c in range(channels):
        img[y1:y2, x1:x2, c] = (alpha * img_overlay[y1o:y2o, x1o:x2o, c] +
                                alpha_inv * img[y1:y2, x1:x2, c])
    
    return img

def posterizeImage(img, level):
    indices = np.arange(0,256)   # List of all colors 
    divider = np.linspace(0,255,level+1)[1] # we get a divider
    quantiz = np.int0(np.linspace(0,255,level)) # we get quantization colors
    color_levels = np.clip(np.int0(indices/divider),0,level-1) # color levels 0,1,2..
    palette = quantiz[color_levels] # Creating the palette
    im2 = palette[img]  # Applying palette on image
    im2 = cv2.convertScaleAbs(im2) # Converting image back to uint8
    return im2
    
def alignImages(reference, toAlign):
    # Convert images to grayscale
    im1Gray = cv2.cvtColor(toAlign, cv2.COLOR_BGR2GRAY)
    im2Gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    # Detect ORB features and compute descriptors.
    orb = cv2.ORB_create(MAX_FEATURES)
    keypoints1, descriptors1 = orb.detectAndCompute(im1Gray, None)
    keypoints2, descriptors2 = orb.detectAndCompute(im2Gray, None)

    # Match features.
    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.match(descriptors1, descriptors2, None)

    # Sort matches by score
    matches.sort(key=lambda x: x.distance, reverse=False)

    # Remove not so good matches
    numGoodMatches = int(len(matches) * GOOD_MATCH_PERCENT)
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
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    return mask

def smoothImage(img, dilate, erode):
    smoothed = img
    smoothed = cv2.dilate(img, kernel, dilate)
    smoothed = cv2.erode(smoothed, kernel, erode)
    return smoothed

width = 1920
height = 1080

blurKSize = (5,5)
blurAmmount = 10

min_countour_area = 2000.0

kernel = np.ones((9,9))

changes =  {
    "death": {
        "lower": (50, 188, 174),
        "upper": (98, 255, 238),
        "color": (0, 255, 255)
    },
    "growth": {
        "lower": (99, 211, 186),
        "upper": (153, 255, 238),
        "color": (0, 255, 0)
    },
    "bleached": {
        "lower": (149, 64, 179),
        "upper": (180, 158, 255),
        "color": (0, 0, 255)
    },
    "healed": {
        "lower": (0, 151, 108),
        "upper": (53, 238, 255),
        "color": (255, 0, 0)
    }
}
expand_amount = 10

coral_reference = cv2.imread("coral_1.png")
coral_to_align = cv2.imread("coral_6.png")

coral_matches, h = alignImages(coral_reference, coral_to_align)

# Apply homography
coral_alinged = cv2.warpPerspective(coral_to_align, h, (width, height))

# cv2.imshow("coral_reference ", coral_reference)
# cv2.imshow("coral_to_align ", coral_to_align)
# cv2.imshow("matches ", coral_matches)
# cv2.imshow("aligned", coral_alinged)
# cv2.imshow("aligned overlay", overlay_image_alpha(coral_reference, coral_alinged[:, :, 0:3], (0, 0), 0.5))
#cv2.imshow("subtraction", coral_subtracted)

coral_subtracted = cv2.GaussianBlur(coral_reference, blurKSize, blurAmmount) - cv2.GaussianBlur(coral_alinged, blurKSize, blurAmmount)

# Mark Changes on the reef
for key in changes:
    mask = HSVThreshold(coral_subtracted, changes[key]["lower"], changes[key]["upper"])
    mask_smooth = smoothImage(mask, dilate=10, erode=10)

    contours, hierarchy = cv2.findContours(mask_smooth, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        if cv2.contourArea(contour) > min_countour_area:
            (x,y,w,h) = cv2.boundingRect(contour)
            x -= expand_amount
            y -= expand_amount
            w += expand_amount*2
            h += expand_amount*2
            cv2.rectangle(coral_alinged, (x,y), (x+w,y+h), changes[key]["color"], 2)

cv2.imshow("coral_annotated", coral_alinged)
cv2.moveWindow("coral_annotated", 1000,50)

cv2.imshow("coral_reference", coral_reference)
cv2.moveWindow("coral_reference", -500,50)


cv2.waitKey(0)
cv2.destroyAllWindows()