"""
Some codes from https://github.com/Newmu/dcgan_code

Released under the MIT license.
"""
from __future__ import division
import random
import pprint
import scipy.misc
import numpy as np
from time import gmtime, strftime
import tensorflow as tf
from mmd import _eps
import time

from six.moves import xrange

pp = pprint.PrettyPrinter()

def safer_norm(tensor, axis=None, keep_dims=False, epsilon=_eps):
    sq = tf.square(tensor)
    squares = tf.reduce_sum(sq, axis=axis, keep_dims=keep_dims)
    return tf.sqrt(squares + epsilon)

def inverse_transform(images):
    return (images+1.)/2.


def save_images(images, size, image_path):
    merged = merge(inverse_transform(images), size)
    return scipy.misc.imsave(image_path, merged)


def merge(images, size):
    h, w = images.shape[1], images.shape[2]
    img = np.zeros((h * size[0], w * size[1], 3))
    for idx, image in enumerate(images):
        i = idx % size[1]
        j = idx // size[1]
        img[j*h:j*h+h, i*w:i*w+w, :] = image

    return img

#def merge(images, size):
#    h, w = images.shape[1], images.shape[2]
#    if (images.shape[3] in (3,4)):
#        c = images.shape[3]
#        img = np.zeros((h * size[0], w * size[1], c))
#        for idx, image in enumerate(images):
#            i = idx % size[1]
#            j = idx // size[1]
#            img[j * h:j * h + h, i * w:i * w + w, :] = image
#        return img
#    elif images.shape[3]==1:
#        img = np.zeros((h * size[0], w * size[1]))
#        for idx, image in enumerate(images):
#            i = idx % size[1]
#            j = idx // size[1]
#            img[j * h:j * h + h, i * w:i * w + w] = image[:,:,0]
#        return img
#    else:
#        raise ValueError('in merge(images,size) images parameter '
#                         'must have dimensions: HxW or HxWx3 or HxWx4')
        
def center_crop(x, crop_h, crop_w,
                resize_h=64, resize_w=64):
    if crop_w is None:
        crop_w = crop_h
    h, w = x.shape[:2]
    j = int(round((h - crop_h)/2.))
    i = int(round((w - crop_w)/2.))
    return scipy.misc.imresize(x[j:j+crop_h, i:i+crop_w], [resize_h, resize_w])

  
def to_json(output_path, *layers):
    with open(output_path, "w") as layer_f:
        lines = ""
        for w, b, bn in layers:
            layer_idx = w.name.split('/')[0].split('h')[1]

            B = b.eval()

            if "lin/" in w.name:
                W = w.eval()
                depth = W.shape[1]
            else:
                W = np.rollaxis(w.eval(), 2, 0)
                depth = W.shape[0]

            biases = {"sy": 1, "sx": 1, "depth": depth,
                      "w": ['%.2f' % elem for elem in list(B)]}
            if bn != None:
                gamma = bn.gamma.eval()
                beta = bn.beta.eval()

                gamma = {"sy": 1, "sx": 1, "depth": depth,
                         "w": ['%.2f' % elem for elem in list(gamma)]}
                beta = {"sy": 1, "sx": 1, "depth": depth,
                         "w": ['%.2f' % elem for elem in list(beta)]}
            else:
                gamma = {"sy": 1, "sx": 1, "depth": 0, "w": []}
                beta = {"sy": 1, "sx": 1, "depth": 0, "w": []}

            if "lin/" in w.name:
                fs = []
                for w in W.T:
                    fs.append({"sy": 1, "sx": 1, "depth": W.shape[0],
                               "w": ['%.2f' % elem for elem in list(w)]})

                lines += """
                    var layer_%s = {
                        "layer_type": "fc",
                        "sy": 1, "sx": 1,
                        "out_sx": 1, "out_sy": 1,
                        "stride": 1, "pad": 0,
                        "out_depth": %s, "in_depth": %s,
                        "biases": %s,
                        "gamma": %s,
                        "beta": %s,
                        "filters": %s
                    };""" % (layer_idx.split('_')[0], W.shape[1], W.shape[0],
                             biases, gamma, beta, fs)
            else:
                fs = []
                for w_ in W:
                    fs.append({"sy": 5, "sx": 5, "depth": W.shape[3],
                               "w": ['%.2f' % elem for elem in list(w_.flatten())]})

                lines += """
                    var layer_%s = {
                        "layer_type": "deconv",
                        "sy": 5, "sx": 5,
                        "out_sx": %s, "out_sy": %s,
                        "stride": 2, "pad": 1,
                        "out_depth": %s, "in_depth": %s,
                        "biases": %s,
                        "gamma": %s,
                        "beta": %s,
                        "filters": %s
                    };""" % (layer_idx, 2**(int(layer_idx)+2), 2**(int(layer_idx)+2),
                             W.shape[0], W.shape[3], biases, gamma, beta, fs)
        layer_f.write(" ".join(lines.replace("'","").split()))


def make_gif(images, fname, duration=2, true_image=False):
    import moviepy.editor as mpy

    def make_frame(t):
        try:
            x = images[int(len(images)/duration*t)]
        except:
            x = images[-1]

        if true_image:
            return x.astype(np.uint8)
        else:
            return ((x+1)/2*255).astype(np.uint8)

    clip = mpy.VideoClip(make_frame, duration=duration)
    clip.write_gif(fname, fps=len(images) / duration)


def visualize(sess, dcgan, config, option):
    if option == 0:
        z_sample = np.random.uniform(-0.5, 0.5, size=(config.batch_size, dcgan.z_dim))
        samples = sess.run(dcgan.sampler, feed_dict={dcgan.z: z_sample})
        time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        save_images(samples, [8, 8], './samples/test_%s.png' % time)
    elif option == 1:
        values = np.arange(0, 1, 1./config.batch_size)
        for idx in xrange(100):
            print(" [*] %d" % idx)
            z_sample = np.zeros([config.batch_size, dcgan.z_dim])
            for kdx, z in enumerate(z_sample):
                z[idx] = values[kdx]

        samples = sess.run(dcgan.sampler, feed_dict={dcgan.z: z_sample})
        save_images(samples, [8, 8], './samples/test_arange_%s.png' % (idx))
    elif option == 2:
        values = np.arange(0, 1, 1./config.batch_size)
        for idx in [random.randint(0, 99) for _ in xrange(100)]:
            print(" [*] %d" % idx)
            z = np.random.uniform(-0.2, 0.2, size=(dcgan.z_dim))
            z_sample = np.tile(z, (config.batch_size, 1))
            #z_sample = np.zeros([config.batch_size, dcgan.z_dim])
            for kdx, z in enumerate(z_sample):
                z[idx] = values[kdx]

            samples = sess.run(dcgan.sampler, feed_dict={dcgan.z: z_sample})
            make_gif(samples, './samples/test_gif_%s.gif' % (idx))
    elif option == 3:
        values = np.arange(0, 1, 1./config.batch_size)
        for idx in xrange(100):
            print(" [*] %d" % idx)
            z_sample = np.zeros([config.batch_size, dcgan.z_dim])
            for kdx, z in enumerate(z_sample):
                z[idx] = values[kdx]

            samples = sess.run(dcgan.sampler, feed_dict={dcgan.z: z_sample})
            make_gif(samples, './samples/test_gif_%s.gif' % (idx))
    elif option == 4:
        image_set = []
        values = np.arange(0, 1, 1./config.batch_size)

        for idx in xrange(100):
            print(" [*] %d" % idx)
            z_sample = np.zeros([config.batch_size, dcgan.z_dim])
            for kdx, z in enumerate(z_sample):
                z[idx] = values[kdx]

        image_set.append(sess.run(dcgan.sampler, feed_dict={dcgan.z: z_sample}))
        make_gif(image_set[-1], './samples/test_gif_%s.gif' % (idx))

    new_image_set = [
        merge(np.array([images[idx] for images in image_set]), [10, 10])
        for idx in range(64) + range(63, -1, -1)]
    make_gif(new_image_set, './samples/test_gif_merged.gif', duration=8)



def unpickle(file):
    import _pickle as cPickle
    fo = open(file, 'rb')
    dict = cPickle.load(fo, encoding='latin1')
    fo.close()
    return dict


def center_and_scale(im, size=64) :
    size = int(size)
    arr = np.array(im)
    scale = min(im.size)/float(size)
    new_size = np.array(im.size)/scale
    im.thumbnail(new_size)
    arr = np.array(im)
    assert min(arr.shape[:2]) == size, "shape error: " + repr(arr.shape) + ", lower dim should be " + repr(size)
#    l0 = int((arr.shape[0] - size)//2)
#    l1 = int((arr.shape[1] - size)//2) 
    l0 = np.random.choice(np.arange(arr.shape[0] - size + 1), 1)[0]
    l1 = np.random.choice(np.arange(arr.shape[1] - size + 1), 1)[0]
    arr = arr[l0:l0 + size, l1: l1 + size, :]
    sh = (size, size, 3)
    assert arr.shape == sh, "shape error: " + repr(arr.shape) + ", should be " + repr(sh)
    return np.asarray(arr/255., dtype=np.float32)


def center_and_scale_new(im, size=64, assumed_input_size=256, channels=3):
    if assumed_input_size is not None:
        ratio = int(assumed_input_size/size)
        decoded = tf.image.decode_jpeg(im, channels=channels, ratio=ratio)
        cropped = tf.random_crop(decoded, size=[size, size, 3])
        return tf.to_float(cropped)/255.
    size = int(size)
    decoded = tf.image.decode_jpeg(im, channels=channels)
    s = tf.reduce_min(tf.shape(decoded)[:2])
    cropped = tf.random_crop(decoded, size=[s, s, 3])
    scaled = tf.image.resize_images(cropped, [size, size])
    return tf.to_float(scaled)/255.
    
    

def read_and_scale(file, size=64):
    from PIL import Image
    im = Image.open(file)
    return center_and_scale(im, size=size)
    
    
def variable_summary(var, name):
    """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
#    with tf.get_variable_scope():
    if var is None:
        print("Variable Summary: None value for variable '%s'" % name)
        return
    var = tf.clip_by_value(var, -1000., 1000.)
    mean = tf.reduce_mean(var)
    with tf.name_scope('absdev'):
        stddev = tf.reduce_mean(tf.abs(var - mean))
    tf.summary.scalar(name + '_absdev', stddev)
#    tf.summary.scalar(name + '_norm', tf.sqrt(tf.reduce_mean(tf.square(var))))
    tf.summary.histogram(name + '_histogram', var)
        
def variable_summaries(variable_dict):
    for name, var in variable_dict.items():
        variable_summary(var, name)        
        
def conv_sizes(size, layers, stride=2):
    s = [int(size)]
    for l in range(layers):
        s.append(int(np.ceil(float(s[-1])/float(stride))))
    return tuple(s)


def get_image(image_path, input_height, input_width,
              resize_height=64, resize_width=64,
              crop=True, grayscale=False):
    image = imread(image_path, grayscale)
    return transform(image, input_height, input_width,
                     resize_height, resize_width, crop)

def imread(path, grayscale = False):
    if (grayscale):
        return scipy.misc.imread(path, flatten = True).astype(np.float)
    else:
        return scipy.misc.imread(path).astype(np.float)

def merge_images(images, size):
    return inverse_transform(images)



def imsave(images, size, path):
    image = np.squeeze(merge(images, size))
    return scipy.misc.imsave(path, image)


def transform(image, input_height, input_width, 
              resize_height=64, resize_width=64, crop=True):
    if crop:
        cropped_image = center_crop(image, input_height, input_width, 
                                    resize_height, resize_width)
    else:
        cropped_image = scipy.misc.imresize(image, [resize_height, resize_width])
    return np.array(cropped_image)/255.

class Loss_variance(object):
    def __init__(self, sess, dim, critic, kernel_name='distance', 
                  batch_sizes=[16, 128, 1024], bootstrap_samples=10):
        import mmd 
        kernel = getattr(mmd, '_%s_kernel' % kernel_name)
        self.loss = {}
        self.kernel_name = kernel_name
        self.bootstrap_samples = bootstrap_samples
        self.sess = sess
        self.history = {}
        for bs in batch_sizes:
            r = tf.Variable(np.zeros((bs, dim)), name='real%d' % bs, 
                            trainable=False, dtype=tf.float32)
            f = tf.Variable(np.zeros((bs, dim)), name='fake%d' % bs, 
                            trainable=False, dtype=tf.float32) 
            self.loss[bs] = mmd.mmd2(kernel(critic(r), critic(f)))
            self.history[bs] = []
    
    def __call__(self, real, fake, mess=''):
        t0 = time.time()
        for bs, loss in self.loss.items():
            assert fake.shape[0] >= self.bootstrap_samples * bs, 'too few generated samples' 
            assert real.shape[0] >= self.bootstrap_samples * bs, 'too few real samples' 
            losses = []
            for i in range(self.bootstrap_samples):
                feed_dict = {'real%d' % bs: real[i*bs: (i+1)*bs],
                             'fake%d' % bs: fake[i*bs: (i+1)*bs]}
                losses.append(self.sess.run(loss, feed_dict=feed_dict))
            mean, std = losses.mean(), losses.std()
            print('%s %s loss for batch size %d: %.5f (%.5f)' % (mess, 
                  self.kernel_name, bs, mean, std))
            self.history[bs].append((mean, std))
        print('%s loss variance evaluation time: %.1f' % mess, time.time() - t0)
        
        
def tf_read_jpeg(files, base_size=160, target_size=64, batch_size=128, 
                 capacity=4000, num_threads=4):
    filename_queue = tf.train.string_input_producer(files)
    reader = tf.WholeFileReader()
    _, raw = reader.read(filename_queue)
    decoded = tf.image.decode_jpeg(raw, channels=3)
    cropped = tf.image.resize_image_with_crop_or_pad(decoded, base_size, base_size)
    
    ims = tf.train.shuffle_batch(
        [cropped], 
        batch_size=batch_size,
        capacity=capacity,
        min_after_dequeue=capacity//4,
        num_threads=4,
        enqueue_many=False
    )
    
    resized = tf.image.resize_bilinear(ims, (target_size, target_size))
    images = tf.cast(resized, tf.float32)/255.
    return images
    
    