import cv2 as cv
import numpy as np
import colorsys
import os

# rescaleFrame: a function that resizes the image window -- change "scale" to make larger/smaller.
def rescaleFrame(frame, scale=0.50):
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)
    dimensions = (width,height)
    return cv.resize(frame, dimensions, interpolation=cv.INTER_AREA)

# change this variable to the folder containing your collagen images. do not delete the quotation marks.
# ensure there are no other files in the folder besides your images. subfolders are OK.
path = 'D:/Collagen/TRF/HA56.5'

# this block of code reads loads your images in the BGR colorspace, and saves the filenames for later.
images, filenames = [], []
for filename in sorted(os.listdir(path)):
    img = cv.imread(os.path.join(path,filename), cv.IMREAD_COLOR)
    if img is not None:
        images.append(img)
        filenames.append(filename)

# this block of code converts the BGR images to HSV for white balancing and thresholding purposes.
hsv_images = []
for img in images:
    hsv_images.append(cv.cvtColor(img, cv.COLOR_BGR2HSV))

# this block of code finds the brightest pixels in the image. we will average these pixels to generate
# ratios with which we can color correct the entire image.
white_pixel_lower_threshold = np.asarray([0,0,250])
white_pixel_upper_threshold = np.asarray([180,100,255])
brightest_pixel_masks, brightest_pixel_coordinates = [], []
for hsv_img in hsv_images:
    brightest_pixel_mask = cv.inRange(hsv_img, white_pixel_lower_threshold, white_pixel_upper_threshold)
    coordinates = list(zip(np.nonzero(brightest_pixel_mask)[0],np.nonzero(brightest_pixel_mask[1])))
    brightest_pixel_masks.append(brightest_pixel_mask)
    brightest_pixel_coordinates.append(coordinates)

# The previous block of code created a list of lists of coordinates. Each coordinate in each image will be added
# to a vector list and averaged out, then rounded. This creates a "white sample" for each image.
hsv_vectors = []
for coordinate_list,hsv_img in zip(brightest_pixel_coordinates,hsv_images):
    for coordinate in coordinate_list:
        hsv_vectors.append(hsv_img[coordinate])

white_points = []
hsv_color_correction_vectors = []
for array in hsv_vectors:
    a = np.array(array)
    white_point = np.mean(a, axis=0)
    rounded_white_point = np.around(white_point, decimals=0)
    hsv_color_correction_vectors.append(rounded_white_point)

# The white sample vectors we created previously are still in HSV color space. The code below converts them
# back to BGR.
bgr_correction_vectors = []
for vector in hsv_color_correction_vectors:
    h,s,v = vector[0]/180, vector[1]/255, vector[2]/255
    rgb_fractional = colorsys.hsv_to_rgb(h,s,v)
    b,g,r = rgb_fractional[2]*255, rgb_fractional[1]*255, rgb_fractional[0]*255
    bgr_correction_vectors.append([b,g,r])

# This block of code creates images coded to our white sample so the user can verify that it is indeed white.
white_sample_images = []
for img,vector in zip(images,bgr_correction_vectors):
    blank_image = np.zeros((250,250,3),np.uint8)
    blank_image[:,:,0] = vector[0]
    blank_image[:,:,1] = vector[1]
    blank_image[:,:,2] = vector[2]
    white_sample_images.append(blank_image)

# Now we calculate ratios by divind max value 255 by our vectors to see what channels need to be increased/decreased.
bgr_ratios = []
for vector in bgr_correction_vectors:
    blue_ratio = 255/vector[0]
    green_ratio = 255/vector[1]
    red_ratio = 255/vector[2]
    bgr_ratios.append([blue_ratio,green_ratio,red_ratio])

# Generates the color corrected images.
color_corrected_imgs = []
for img, ratio in zip(images, bgr_ratios):
    blue = cv.multiply(img[...,0],ratio[0])
    green = cv.multiply(img[...,1],ratio[1])
    red = cv.multiply(img[...,2],ratio[2])
    corrected = cv.merge([blue,green,red])
    color_corrected_imgs.append(corrected)

for img, filename, blank, corrected in zip(images,filenames,white_sample_images,color_corrected_imgs):
    cv.imshow(filename,rescaleFrame(img))
    cv.imshow('Color Corrected',rescaleFrame(corrected))
    cv.imshow('White Sample', blank)
    cv.waitKey(0)
    cv.destroyAllWindows()

proceed = input('OK to Proceed? (y/n): ')
if proceed == 'y':
    pass
else:
    exit()

# Assuming the color correction is satisfactory, we can apply a color threshold to determine which pixels
# are collagen and which ones are not.
color_corrected_hsv, masks = [], []
for img in color_corrected_imgs:
    color_corrected_hsv.append(cv.cvtColor(img, cv.COLOR_BGR2HSV))
collagen_lower_threshold = np.asarray([130, 50, 20])
collagen_upper_threshold = np.asarray([180, 255, 255])
for img in color_corrected_hsv:
    mask = cv.inRange(img, collagen_lower_threshold, collagen_upper_threshold)
    masks.append(mask)
collagen = []
for mask in masks:
    collagen.append(cv.countNonZero(mask))

# total pixels in first image. assumes all images being analyzed are same resolution.
x = images[0].shape[1]
y = images[0].shape[0]
total_pixels = x*y

# Apply a second threshold similar to the one earlier to detect white pixels.
white_pixel_lower_threshold2 = np.asarray([0,0,245])
white_pixel_upper_threshold2 = np.asarray([180,40,255])
whitespace, whitespace_images = [], []
for img in color_corrected_hsv:
    whitespace_image = cv.inRange(img,white_pixel_lower_threshold2,white_pixel_upper_threshold2)
    whitespace.append(cv.countNonZero(whitespace_image))
    whitespace_images.append(whitespace_image)

percent_collagen = [100*(i/(total_pixels-j)) for i,j in zip(collagen, whitespace)]
for name, percentage, whitepix, colpix in zip(sorted(os.listdir(path)), percent_collagen, whitespace, collagen):
    print('Filename:', name, '\n', 'Percent Collagen:', percentage, '\n', 'WhitePix:', whitepix, '\n',
          'CollagenPix:', colpix, '\n')

results = []
for img, mask, filename in zip(color_corrected_hsv, masks, sorted(os.listdir(path))):
    blend = cv.addWeighted(cv.cvtColor(img, cv.COLOR_HSV2BGR),
            0.95, cv.cvtColor(mask, cv.COLOR_GRAY2BGR), 0.05, 0.0)
    blend[mask>0]=(0,0,255)
    results.append(blend)
view = input('See results? (y/n): ')
if view == 'y':
    for result, whiteimg, filename in zip(results, whitespace_images, sorted(os.listdir(path))):
        cv.imshow(filename, rescaleFrame(result))
        cv.imshow('Whitespace', rescaleFrame(whiteimg))
        cv.waitKey(0)
        cv.destroyWindow(filename)
        cv.destroyWindow('Whitespace')
else:
    pass

save = input('Save results? (y/n): ')
if save == 'y':
    save_paths = []
    new_dir = path + '/Results'
    np.savetxt(path + '/Results.csv', np.column_stack((filenames, collagen, whitespace, percent_collagen)),
               delimiter=',', fmt='%s', header='Filename')
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    for filename in filenames:
        save_paths.append(new_dir + '/' + filename)
    for save_path, result in zip(save_paths, results):
        cv.imwrite(save_path, result)