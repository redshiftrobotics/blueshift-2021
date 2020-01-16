# Line Following Settings
import cv2
import numpy as np

# Line Following Settings
lf_lower_blue = np.array([70,119,87])
lf_upper_blue = np.array([109,255,225])
lf_kernel = np.ones((3,3), np.uint8)
lf_min_countour_area = 20000.0
lf_percent_of_image_blue_lines_should_fill = 0.75 # Equal to (total_width - blue_to_red_dist) / total_width
lf_target_angle = 90.0

# Given a slope and a point, this function returns a point that on that line with a specific value on the specified axis (https://www.mathsisfun.com/algebra/line-equation-point-slope.html)
def point_slope_line(pt,sl,num,given_axis):
    if given_axis == "x":
        return (num, int(sl*(num-pt[0]) + pt[1]))
    elif given_axis == "y":
        return (int((num-pt[1])/sl + pt[0]), num)

def detectLines(img, cvOutLevel=False, debug=False):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lf_lower_blue, lf_upper_blue)

    filtered = cv2.erode(mask, lf_kernel, iterations=1)
    filtered = cv2.dilate(filtered, lf_kernel, iterations=15)
    filtered = cv2.erode(filtered, lf_kernel, iterations=9)

    contours, hierarchy = cv2.findContours(filtered, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # This will contain points on each line in the format: start, end, middle, and slope
    lines = []

    if len(contours) > 0:
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

                if debug:
                    # Draw the line on the image
                    cv2.line(img, line_top, line_bottom, (0,0,0) ,5)
                    # Draw the center on the image
                    cv2.line(img,(x,y),(x,y),(0,255,0),10)

                # Append the start, end, middle, and slope of each line to the array
                lines.append([np.array(line_top), np.array(line_bottom), np.array([x,y]), slope])
        
        # Display images for debugging
        if debug:
            cv2.imshow("Input", img)
            cv2.moveWindow("Input", 50,50)

            cv2.imshow("Mask", filtered)
            cv2.moveWindow("Mask", 500,50)

            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
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

        if cvOutLevel:
            if cvOutLevel == "Original":
                return line_dist, avg_angle-lf_target_angle, img
            elif cvOutLevel == "Mask":
                return line_dist, avg_angle-lf_target_angle, mask
            elif cvOutLevel == "Smooth":
                return line_dist, avg_angle-lf_target_angle, filtered
            elif cvOutLevel == "Contours":
                return line_dist, avg_angle-lf_target_angle, cv2.drawContours(img, contours, -1, (0,255,0), 3)
        else:
            return line_dist, avg_angle-lf_target_angle
    return None
