import cv2
import numpy as np
 
def cropImage(img, x1,y1,x2,y2):
    return img[y1:y2, x1:x2]

def overlay_image_alpha(img, img_overlay, pos, alpha_mask):
    """Overlay img_overlay on top of img at the position specified by
    pos and blend using alpha_mask.

    Alpha mask must contain values within the range [0, 1] and be the
    same size as img_overlay.
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

    alpha = alpha_mask#[y1o:y2o, x1o:x2o]
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
    
def alignImages(reference, toAlign, toAlignMask):
    # Convert images to grayscale
    im1Gray = cv2.cvtColor(toAlign, cv2.COLOR_BGR2GRAY)
    im2Gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    # Detect ORB features and compute descriptors.
    detector = None
    try:
        detector = cv2.xfeatures2d.SIFT_create()
    except:
        detector = cv2.ORB_create(MAX_FEATURES)
    keypoints1, descriptors1 = detector.detectAndCompute(im1Gray, mask=toAlignMask)
    keypoints2, descriptors2 = detector.detectAndCompute(im2Gray, mask=None)

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
    smoothed = cv2.dilate(img, kernel, dilate)
    smoothed = cv2.erode(smoothed, kernel, erode)
    return smoothed

MAX_FEATURES = 10000
GOOD_MATCH_PERCENT = 0.15

width = 1920
height = 1080

blurKSize = (5,5)
blurAmmount = 10

min_countour_area = 2000.0

kernel = np.ones((9,9))

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

expand_amount = 10

coral_reference = cv2.imread("coral_7.png")

coral_to_align = cv2.imread("coral_7-difficult.png")
coral_to_align_mask = (HSVThreshold(coral_to_align, background_mask["bleached"]["lower"], background_mask["bleached"]["upper"]) +
                       HSVThreshold(coral_to_align, background_mask["healthy"]["lower"], background_mask["healthy"]["upper"]))

coral_to_align_mask = cv2.erode(coral_to_align_mask, kernel, 1)
coral_to_align_mask = cv2.dilate(coral_to_align_mask, kernel, 10)
coral_to_align_mask = cv2.dilate(coral_to_align_mask, kernel, 1)
coral_to_align_masked = cv2.bitwise_and(coral_to_align, coral_to_align, mask=coral_to_align_mask)

coral_matches, h = alignImages(coral_reference, coral_to_align, coral_to_align_mask)

# Apply homography
coral_aligned_mask = cv2.warpPerspective(coral_to_align_masked, h, (width, height))
coral_aligned = cv2.warpPerspective(coral_to_align, h, (width, height))

coral_subtracted = cv2.GaussianBlur(coral_reference, blurKSize, blurAmmount).astype("float16") - cv2.GaussianBlur(coral_aligned_mask, blurKSize, blurAmmount).astype("float16")

coral_subtracted = np.clip(np.abs(coral_subtracted+64), 0, 255).astype("uint8")


# Mark Changes on the reef
for key in changes:
    mask = HSVThreshold(coral_subtracted, changes[key]["filters"][0]["lower"], changes[key]["filters"][0]["upper"])

    if len(changes[key]["filters"]) > 1:
        for colorFilter in changes[key]["filters"]:
            mask = cv2.bitwise_or(mask, HSVThreshold(coral_subtracted, colorFilter["lower"], colorFilter["upper"]))
    
    mask_smooth = cv2.erode(mask, kernel, 1)
    mask_smooth = cv2.dilate(mask_smooth, kernel, 1)
    mask_smooth = cv2.dilate(mask_smooth, kernel, 1)

    contours, hierarchy = cv2.findContours(mask_smooth, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        if cv2.contourArea(contour) > min_countour_area:
            (x,y,w,h) = cv2.boundingRect(contour)
            x -= expand_amount
            y -= expand_amount
            w += expand_amount*2
            h += expand_amount*2
            cv2.rectangle(coral_aligned, (x,y), (x+w,y+h), changes[key]["color"], 2)

# cv2.imshow("coral_reference ", coral_reference)
# cv2.imshow("coral_to_align ", coral_to_align)
# cv2.imshow("coral_to_align_masked", coral_to_align_masked)
# cv2.imshow("matches ", coral_matches)
# cv2.imshow("aligned", coral_aligned_mask)
# cv2.imshow("aligned overlay", overlay_image_alpha(coral_reference, coral_aligned_mask[:, :, 0:3], (0, 0), 0.5))
# cv2.imshow("subtraction", coral_subtracted)

cv2.imshow("coral_annotated", coral_aligned)
cv2.moveWindow("coral_annotated", 1000,50)

cv2.imshow("coral_reference", coral_reference)
cv2.moveWindow("coral_reference", -500,50)

cv2.waitKey(0)
cv2.destroyAllWindows()
