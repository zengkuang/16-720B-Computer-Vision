import os
import math
import time
import random
import multiprocessing

import imageio
import skimage
import numpy as np
import scipy.ndimage
import sklearn.cluster
import scipy.spatial.distance
import matplotlib.pyplot as plt

import util

# Globals
PROGRESS = 0
PROGRESS_LOCK = multiprocessing.Lock()

def extract_filter_responses(image):
    '''
    Extracts the filter responses for the given image.

    [input]
    * image: numpy.ndarray of shape (H,W) or (H,W,3)
    [output]
    * filter_responses: numpy.ndarray of shape (H,W,3F)
    '''

    # Gaussian SD (sigma) values
    sigmas = [1, 2, 4, 8, 8*math.sqrt(2)]

    # Convert grayscale images to 3 channels
    if len(image.shape) < 3:
        image = np.dstack([image] * 3)

    # Convert higher channel images to 3 channels
    if image.shape[2] > 3:
        image = image[:, :, :3]
    
    # Convert RGB to LAB color space
    image_lab = skimage.color.rgb2lab(image)

    filter_responses = []
    for sigma in sigmas:
        # Gaussian filter
        for i in range(0, 3): 
            filter_responses.append(scipy.ndimage.gaussian_filter(image_lab[:, :, i], sigma=sigma))
        
        # Laplacian of gaussian filter
        for i in range(0, 3): 
            filter_responses.append(scipy.ndimage.gaussian_laplace(image_lab[:, :, i], sigma=sigma))
        
        # X axis derivative of gaussian + gaussian filter
        for i in range(0, 3): 
            temp = scipy.ndimage.gaussian_filter1d(image_lab[:, :, i], sigma=sigma, axis=1, order=1)
            filter_responses.append(scipy.ndimage.gaussian_filter1d(temp, sigma=sigma, axis=0))
        
        # Y axis derivative of gaussian + gaussian filter
        for i in range(0, 3): 
            temp = scipy.ndimage.gaussian_filter1d(image_lab[:, :, i], sigma=sigma, axis=0, order=1)
            filter_responses.append(scipy.ndimage.gaussian_filter1d(temp, sigma=sigma, axis=1))

    # Stack all 4 filters * 3 channels * 5 sigmas (60) channels
    filter_responses = np.dstack(filter_responses)
    return filter_responses

def get_visual_words(image, dictionary):
    '''
    Compute visual words mapping for the given image using the dictionary of visual words.

    [input]
    * image: numpy.ndarray of shape (H,W) or (H,W,3)
    
    [output]
    * wordmap: numpy.ndarray of shape (H,W)
    '''
    
    # ----- TODO -----
    pass

def compute_dictionary_one_image(args):
    '''
    Extracts random samples of the dictionary entries from an image.
    This is a function run by a subprocess.

    [input]
    * i: index of training image
    * alpha: number of random samples
    * image_path: path of image file
    * time_start: time stamp of start time

    [saved]
    * sampled_response: numpy.ndarray of shape (alpha, 3F)
    '''

    global PROGRESS
    with PROGRESS_LOCK: PROGRESS += 8

    i, alpha, image_path = args
    print('Processing: %04d/1440 | Index: %04d | Path: %s'%(PROGRESS, i, image_path))

    # Read image
    image = skimage.io.imread('../data/' + image_path)
    image = image.astype('float')/255
    
    # Extract filter responses
    filter_responses = extract_filter_responses(image)

    # Randomly select alpha responses for all channels
    sampled_response = []
    for j in range(alpha):
        ran_h = np.random.choice(image.shape[0])
        ran_w = np.random.choice(image.shape[1])
        sampled_response.append(filter_responses[ran_h, ran_w, :])
    
    # Save the sampled responses
    np.save('../data/sampled_responses/%d'%i, np.asarray(sampled_response))

def compute_dictionary(num_workers=2):
    '''
    Creates the dictionary of visual words by clustering using k-means.

    [input]
    * num_workers: number of workers to process in parallel
    
    [saved]
    * dictionary: numpy.ndarray of shape (K, 3F)
    '''

    # Load train images data
    train_data = np.load('../data/train_data.npz')

    # Create folders to save filter responses
    if not os.path.exists('../data/sampled_responses'):
        os.makedirs('../data/sampled_responses')

    # Multiprocess feature extraction and sampling
    args = [ (i, 50, train_data['image_names'][i][0]) for i in range(train_data['image_names'].shape[0]) ]
    pool = multiprocessing.Pool(processes=num_workers)
    pool.map(compute_dictionary_one_image, args)
    pool.close()
    pool.join()