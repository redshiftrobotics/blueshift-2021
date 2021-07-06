import numpy as np
import cv2
from numpy.lib.function_base import average
import functions


img = cv2.imread('15.png')
img2 = cv2.imread('10.png')
img3 = cv2.imread('12.png')
img4 = cv2.imread('3.png')
img5 = cv2.imread('2.png')
black = cv2.imread('black.jpg')
# img3 = cv2.imread('subwayCarIMG.jpg') 8, 11,12 - bronze & red orange, 14- yellow

colors1, colorPos1, drawing1 = functions.readImage(img)
colors2, colorPos2, drawing2 = functions.readImage(img2)
colors3, colorPos3, drawing3 = functions.readImage(img3)
colors4, colorPos4, drawing4 = functions.readImage(img4)
colors5, colorPos5, drawing5 = functions.readImage(img5)

# print(colors1, colorPos1)
# print(colors2, colorPos2)
# print(colors3, colorPos2)

all_img_colors = [colors1, colors2, colors3, colors4, colors5]
all_imgs = [drawing1, drawing2, drawing3, drawing4, drawing5]
all_img_pos = [colorPos1, colorPos2, colorPos3, colorPos4, colorPos5]

img1, threeColorImgs = functions.stitchImage(all_img_colors, all_imgs, all_img_pos)
img2 = threeColorImgs[0]
img3 = threeColorImgs[1]
img4 = threeColorImgs[2]
img5 = threeColorImgs[3]

im_tile_resize = functions.concat_tile_resize([[img1, black, black, black],
                                     [img2, img3, img4, img5]])
                                     

cv2.imshow('concat_tile_resize.jpg', im_tile_resize)

cv2.waitKey(0)
cv2.destroyAllWindows()



#plan
#find edges
#find all colors on img
# find location of colors on img
#some how stich different imgs together based on that. 

#first find wich two pannels have the same colors.
#find location of the 