import numpy as np
import cv2

def CropImg(img):

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    outlineNum = 0

    lower_white = np.array([0,0, 165])
    upper_white = np.array([179,255, 255])

    outline_mask = cv2.inRange(hsv, lower_white, upper_white)

    outline_mask = cv2.erode(outline_mask, None, iterations=10)
    outline_mask = cv2.dilate(outline_mask, None, iterations=10)
    outline_contours, hierarchy = cv2.findContours(outline_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    vertex= []
    rectangle_areas = []
    for contour in outline_contours:
        (x,y,w,h) = cv2.boundingRect(contour)
        vertex.append((x,y,w,h))
        area = abs(h*w)
        rectangle_areas.append(area)

    max_area_index = rectangle_areas.index(max(rectangle_areas))

    x = vertex[max_area_index][0]
    y = vertex[max_area_index][1]
    w = vertex[max_area_index][2]
    h = vertex[max_area_index][3]

    outline_drawing = cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

    cropped = outline_drawing[y:h+y, x:w+x]

    if abs(cropped.shape[0] - cropped.shape[1]) < 0.5*cropped.shape[1]:
        width = 250
        height = 250
        dim = (width, height)
        
        # resize image
        cropped = cv2.resize(cropped, dim, interpolation = cv2.INTER_AREA)
        # print('Resized Dimensions : ',cropped.shape)

    else:
        width = 500
        height = 250
        dim = (width, height)
        
        # resize image
        cropped = cv2.resize(cropped, dim, interpolation = cv2.INTER_AREA)
 


    return cropped



def findPos(hsv, cropped, lower_color, upper_color, imgColors, color):
    color_mask = cv2.inRange(hsv, lower_color, upper_color)

    color_mask = cv2.erode(color_mask, None, iterations=6)
    color_mask = cv2.dilate(color_mask, None, iterations=6)

    color_contours, hierarchy = cv2.findContours(color_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    color_drawing = cv2.drawContours(cropped, color_contours, -1, (225,255,0), 6)

    total_x = 0
    total_y = 0
    contour_pos = ''

    if color_contours:
        imgColors.append(color)
        new_color_contours = color_contours[0]

        for i in range(len(new_color_contours)):
            total_x = total_x + new_color_contours[i][0][0]
            total_y = total_y + new_color_contours[i][0][1]
        
        average_x = total_x/len(new_color_contours)
        average_y = total_y/len(new_color_contours)
        img_x = cropped.shape[1]
        img_y = cropped.shape[0]
 
      

        if average_y < img_y/4 and average_x > img_x/5 and average_x < 4*img_x/5:
            contour_pos = 'top' 

        elif average_y > 3*img_y/4 and average_x > img_x/5 and average_x < 4*img_x/5:
            contour_pos = 'bottom' 

        elif average_x < img_x/4 and average_y < 4*img_y/5 and average_y > img_y/5:
            contour_pos = 'left'
            # print('left')
        
        elif average_x > img_x/4 and average_y < 4*img_y/5 and average_y > img_y/5:
            contour_pos = 'right'

        else:
            print('something went wrong with'+color)


    # print(color + 'position:', contour_pos)

    return contour_pos, color_drawing




def readImage(img):
    lower_white = np.array([0,0, 113])
    upper_white = np.array([50,96, 206])

    lower_blue = np.array([56,245, 0])
    upper_blue = np.array([138, 255, 255])

    lower_orange = np.array([9,195, 188])
    upper_orange = np.array([22,248, 240])

    lower_green = np.array([77,125, 71])
    upper_green = np.array([96,240, 134])

    lower_pink = np.array([161,72, 184])
    upper_pink = np.array([169,117, 232])

    lower_red = np.array([12,130, 164])
    upper_red = np.array([179,212, 224])

    lower_purple = np.array([121,96, 104])
    upper_purple = np.array([166,181, 159])

    lower_yellow = np.array([14,150, 0])
    upper_yellow = np.array([31,250, 255])

    lower_black = np.array([0,34, 32])
    upper_black = np.array([179,99, 79])

    lower_bronze = np.array([0,80, 124])
    upper_bronze = np.array([27,146, 180])

    
    contours_pos = []
    imgColors = []
    cropped = CropImg(img)
    hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)
    blue_pos, blue_drawing = findPos(hsv, cropped, lower_blue, upper_blue, imgColors, 'blue')
    green_pos, green_drawing = findPos(hsv, cropped, lower_green, upper_green, imgColors, 'green')
    orange_pos, orange_drawing = findPos(hsv, cropped, lower_orange, upper_orange, imgColors, 'orange')
    pink_pos, pink_drawing = findPos(hsv, cropped, lower_pink, upper_pink, imgColors, 'pink')
    purple_pos, purple_drawing = findPos(hsv, cropped, lower_purple, upper_purple, imgColors, 'purple')
    yellow_pos, yellow_drawing = findPos(hsv, cropped, lower_yellow, upper_yellow, imgColors, 'yellow')
    red_pos, red_drawing = findPos(hsv, cropped, lower_red, upper_red, imgColors, 'red')
    black_pos, black_drawing = findPos(hsv, cropped, lower_black, upper_black, imgColors, 'black')
    bronze_pos, bronze_drawing = findPos(hsv, cropped, lower_bronze, upper_bronze, imgColors, 'bronze')
    contours_pos.append(blue_pos)
    contours_pos.append(green_pos)
    contours_pos.append(orange_pos)
    contours_pos.append(pink_pos)
    contours_pos.append(purple_pos)
    contours_pos.append(yellow_pos)
    contours_pos.append(red_pos)
    contours_pos.append(black_pos)
    contours_pos.append(bronze_pos)

    contours_pos = list(filter(None, contours_pos))
    

    if len(imgColors) == 3 and any('bottom' in s for s in contours_pos):
        blue_drawing = cv2.rotate(blue_drawing, cv2.ROTATE_180)
        for i in range(len(contours_pos)):
            if contours_pos[i] == 'left':
                contours_pos[i] = 'right'

            elif contours_pos[i] == 'right':
                contours_pos[i] = 'left'
            
            elif contours_pos[i] == 'top':
                contours_pos[i] = 'bottom'
            
            elif contours_pos[i] == 'bottom':
                contours_pos[i] = 'top'
    else:
        pass


    return imgColors, contours_pos, blue_drawing

    black = cv2.imread('black.jpg')
def stitchImage(all_img_colors, all_imgs, all_img_pos):
    for i in range(len(all_img_colors)):
        colorNum = len(all_img_colors[i])
        # print('color number: ', colorNum)
        if colorNum == 4:
            imgOne = all_imgs[i]
          
           
            theColor = all_img_colors[i][all_img_pos[i].index('bottom')]
            del all_imgs[i]
            del all_img_colors[i]
            del all_img_pos[i]
            
            threeColorImgs = stitchThreeColorImgs(theColor, all_imgs, all_img_colors, all_img_pos)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            return imgOne, threeColorImgs
           

        else:
            pass
    

def loop(theColor, all_imgs, all_img_colors, all_img_pos, threeColorImgs):
     for i in range(len(all_img_colors)):
        if theColor in all_img_colors[i]:
            threeColorImgs.append(all_imgs[i])
            theColor = all_img_colors[i][all_img_pos[i].index('right')]
            all_imgs.pop(i)
            all_img_colors.pop(i)
            all_img_pos.pop(i)
            return theColor, all_imgs, all_img_colors, all_img_pos, threeColorImgs

def stitchThreeColorImgs(theColor, all_imgs, all_img_colors, all_img_pos):
    threeColorImgs = []
    theRange = len(all_img_colors)
    for i in range(theRange):
        theColor, all_imgs, all_img_colors, all_img_pos, threeColorImgs = loop(theColor, all_imgs, all_img_colors, all_img_pos, threeColorImgs)
    
    else:
        pass    
    print('3colorslen: ', len(threeColorImgs))

    return threeColorImgs
   


def hconcat_resize(img_list, 
                   interpolation 
                   = cv2.INTER_CUBIC):
      # take minimum hights
    h_min = min(img.shape[0] 
                for img in img_list)
      
    # image resizing 
    im_list_resize = [cv2.resize(img,
                       (int(img.shape[1] * h_min / img.shape[0]),
                        h_min), interpolation
                                 = interpolation) 
                      for img in img_list]
      
    # return final image
    return cv2.hconcat(im_list_resize)

def vconcat_resize(img_list, interpolation 
                   = cv2.INTER_CUBIC):
      # take minimum width
    w_min = min(img.shape[1] 
                for img in img_list)
      
    # resizing images
    im_list_resize = [cv2.resize(img,
                      (w_min, int(img.shape[0] * w_min / img.shape[1])),
                                 interpolation = interpolation)
                      for img in img_list]
    # return final image
    return cv2.vconcat(im_list_resize)

def concat_tile_resize(list_2d, 
                       interpolation = cv2.INTER_CUBIC):
      # function calling for every 
    # list of images
    img_list_v = [hconcat_resize(list_h, 
                                 interpolation = cv2.INTER_CUBIC) 
                  for list_h in list_2d]
      
    # return final image
    return vconcat_resize(img_list_v, interpolation=cv2.INTER_CUBIC)