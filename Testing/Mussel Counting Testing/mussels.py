import numpy as np
import cv2
mussel_numbers = 0


# Load an color image in grayscale
img = cv2.imread('mussels_orange.jpg')
cv2.imshow('image',img)

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

lower_white = np.array([0,34, 161])
upper_white = np.array([355, 141, 255])

lower_orange = np.array([10,90,164])
upper_orange = np.array([255,255,255])

mussel_mask = cv2.inRange(hsv, lower_white, upper_white)
quadrat_mask = cv2.inRange(hsv, lower_orange, upper_orange)

mussel_mask = cv2.erode(mussel_mask, None, iterations=2)
mussel_mask = cv2.dilate(mussel_mask, None, iterations=3)

#create quadrat contours 
quadrat_contours, hierarchy = cv2.findContours(quadrat_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

#delete extra contours
contour_areas= []
for contour in quadrat_contours:
    area = cv2.contourArea(contour)
    contour_areas.append(area)

max_contour = contour_areas.index(max(contour_areas))

del quadrat_contours[max_contour]
del contour_areas[max_contour]

inner_contour_index = contour_areas.index(max(contour_areas))

quadrat_contours = [quadrat_contours[inner_contour_index]]

#drawing quadrat contours
quadrat_drawing = cv2.drawContours(img.copy(), quadrat_contours, -1, (0,255,0), 3)

#creat img that is white inside of the quadrat contours and black overywhere else.
white = [255,255,255]
mask = np.zeros_like(img)
contour_mask = cv2.drawContours(mask, quadrat_contours, 0, white, -1) # Draw filled contour in mask

#converting contour_mask from rgb to hsv
hsv_white = cv2.cvtColor(contour_mask.copy(), cv2.COLOR_BGR2HSV)
lower_white = np.array([0,0,184])
upper_white = np.array([359, 225, 255])
quadrat_area_mask = cv2.inRange(hsv_white, lower_white, upper_white)

mussels_in_quadrat = np.logical_and(mussel_mask, quadrat_area_mask)
mussels_in_quadrat = mussels_in_quadrat.astype(np.uint8)

#converting 0s and 1s to 0s and 255s
mussels_in_quadrat = mussels_in_quadrat*255

#creating and drawing contours around mussels
mussel_contours, hierarchy = cv2.findContours(mussels_in_quadrat.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
drawing = cv2.drawContours(mussels_in_quadrat.copy(),mussel_contours, -1, (225,255,0), 3)

cv2.imshow('final img', drawing)

#counting mussels
for i in range(len(mussel_contours)):
    mussel_numbers += 1
mussel_numbers = str(mussel_numbers)
print("There are " + mussel_numbers + " mussels whithin this quadrat.")



cv2.waitKey(0)
cv2.destroyAllWindows()
