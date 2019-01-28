import tensorflow as tf
from data_loader import Data_loader
from model import get_model
import time
from tensorflow.contrib import autograph

def weighted_cross_entropy(y_pred, y_gt):
	l = tf.reduce_sum(tf.multiply(y_gt, tf.log(y_pred)), axis=1)
	l = tf.reduce_sum(l, axis=1)
	l = tf.reduce_sum(l, axis=1)
	n = tf.reduce_sum(y_gt, axis=1)
	n = tf.reduce_sum(n, axis=1)
	n = tf.reduce_sum(n, axis=1)
	l = -1 * tf.reduce_sum(l / n)


def total_loss(y_pred, p_gt):
	return weighted_cross_entropy(y_pred, y_gt) + weighted_cross_entropy((1 - y_pred), (1 - y_gt))


@autograph.convert(recursive=True)
def train(data_path, batch_size, max_steps, lr=10e-5):
	texture, ref, label, decode_mask = get_model()
	dl_train = Data_loader(data_path['train'], batch_size)
	dl_val = Data_loader(data_path['val'], batch_size)
	opt = tf.train.AdamOptimizer(lr)

	loss = total_loss(decode_mask, label)
	train_op = opt.minimize(loss)

	saver = tf.train.Saver()
	init = tf.global_variables_initializer()
	config = tf.ConfigProto()
	config.gpu_options.allow_growth = True

	best_loss = np.inf
	loss_log = {'train':[], 'val':[]}
	with tf.Session() as sess:
		sess.run(init)
		cur_train_loss = 0
		tic = time.time()
		for i in range(max_steps):
			data = dl_train.get_batch_data()	# batch, mask, ref
			_, train_loss = sess.run([train_op, loss], feed_dict={texture: data[0], ref:data[2], label: data[1]})
			cur_train_loss += train_loss

			if i % 5000 == 0:
				toc = time.time()
				# evaluate validation loss for 100 step
				val_loss = 0
				for i in range(100):
					test_data = dl_val.get_batch_data()
					val_loss += sess.run(loss, feed_dict={texture: test_data[0], ref:test_data[2], label: test_data[1]})
				val_loss /= batch_size * 100
				if val_loss < best_loss:
					best_loss = val_loss
					print('saving best model (%.5f)' % best_loss)
					saver.save(sess, '/fast_data/one_shot_texture_models/best_model')

				cur_train_loss /= batch_size * 5000

				print('%7d/%7d training loss: %.5f, validation loss: %.5f (%d sec)' % (i, max_steps, cur_train_loss, val_loss, toc - tic))
				loss_log['train'].append(cur_train_loss)
				loss_log['val'].append(val_loss)

				cur_train_loss = 0

				saver.save(sess, '/fast_data/one_shot_texture_models/model', global_step=i)

				tic = time.time()

	np.save('train_log', loss_log['train'])
	np.save('val_log', loss_log['val'])

if __name__ == '__main__':
	data_path = {
		'train': 'train_texture.npy',
		'val': 'val_texture.npy'
	}
	train(data_path, 32, 2000000)