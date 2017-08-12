import tensorflow as tf
import selu
import param

class Clairvoyante(object):

    def __init__(self, inputShape = (2*param.flankingBaseNum+1, 4, param.matrixNum),
                       outputShape1 = (4, ), outputShape2 = (5, ),
                       kernelSize1 = (1, 4), kernelSize2 = (2, 4), kernelSize3 = (3, 4),
                       pollSize1 = (5, 1), pollSize2 = (4, 1), pollSize3 = (3, 1),
                       numFeature1 = 16, numFeature2 = 32, numFeature3 = 48,
                       hiddenLayerUnits4 = 336, hiddenLayerUnits5 = 84,
                       initialLearningRate = param.initialLearningRate,
                       learningRateDecay = param.learningRateDecay,
                       dropoutRate = param.dropoutRate):
        self.inputShape = inputShape
        self.outputShape1 = outputShape1; self.outputShape2 = outputShape2
        self.kernelSize1 = kernelSize1; self.kernelSize2 = kernelSize2; self.kernelSize3 = kernelSize3
        self.pollSize1 = pollSize1; self.pollSize2 = pollSize2; self.pollSize3 = pollSize3
        self.numFeature1 = numFeature1; self.numFeature2 = numFeature2; self.numFeature3 = numFeature3
        self.hiddenLayerUnits4 = hiddenLayerUnits4; self.hiddenLayerUnits5 = hiddenLayerUnits5
        self.learningRateVal = initialLearningRate
        self.learningRateDecay = learningRateDecay
        self.dropoutRateVal = dropoutRate
        self.g = tf.Graph()
        self._buildGraph()
        self.session = tf.Session(graph = self.g)

    def _buildGraph(self):
        with self.g.as_default():
            XPH = tf.placeholder(tf.float32, [None, self.inputShape[0], self.inputShape[1], self.inputShape[2]])
            self.XPH = XPH

            YPH = tf.placeholder(tf.float32, [None, self.outputShape1[0] + self.outputShape2[0]])
            self.YPH = YPH

            learningRatePH = tf.placeholder(tf.float32, shape=[])
            self.learningRatePH = learningRatePH

            phasePH = tf.placeholder(tf.bool, shape=[])
            self.phasePH = phasePH

            dropoutRatePH = tf.placeholder(tf.float32, shape=[])
            self.dropoutRatePH = dropoutRatePH

            conv1 = tf.layers.conv2d(inputs=XPH,
                                     filters=self.numFeature1,
                                     kernel_size=self.kernelSize1,
                                     kernel_initializer = tf.truncated_normal_initializer(stddev=0.01, dtype=tf.float32),
                                     padding="same",
                                     activation=selu.selu)

            pool1 = tf.layers.max_pooling2d(inputs=conv1,
                                            pool_size=self.pollSize1,
                                            strides=1)

            conv2 = tf.layers.conv2d(inputs=pool1,
                                     filters=self.numFeature2,
                                     kernel_size=self.kernelSize2,
                                     kernel_initializer = tf.truncated_normal_initializer(stddev=0.01, dtype=tf.float32),
                                     padding="same",
                                     activation=selu.selu)

            pool2 = tf.layers.max_pooling2d(inputs=conv2,
                                            pool_size=self.pollSize2,
                                            strides=1)

            conv3 = tf.layers.conv2d(inputs=pool2,
                                     filters=self.numFeature3,
                                     kernel_size=self.kernelSize3,
                                     kernel_initializer = tf.truncated_normal_initializer(stddev=0.01, dtype=tf.float32),
                                     padding="same",
                                     activation=selu.selu)

            pool3 = tf.layers.max_pooling2d(inputs=conv3,
                                            pool_size=self.pollSize3,
                                            strides=1)

            flat_size = ( self.inputShape[0] - (self.pollSize1[0] - 1) - (self.pollSize2[0] - 1) - (self.pollSize3[0] - 1))
            flat_size *= ( self.inputShape[1] - (self.pollSize1[1] - 1) - (self.pollSize2[1] - 1) - (self.pollSize3[1] - 1))
            flat_size *= self.numFeature3
            conv3_flat =  tf.reshape(pool3, [-1,  flat_size])

            fc4 = tf.layers.dense(inputs=conv3_flat,
                                 units=self.hiddenLayerUnits4,
                                 kernel_initializer = tf.truncated_normal_initializer(stddev=0.01, dtype=tf.float32),
                                 activation=selu.selu)

            dropout4 = selu.dropout_selu(fc4, dropoutRatePH, training=phasePH)

            fc5 = tf.layers.dense(inputs=dropout4,
                                 units=self.hiddenLayerUnits5,
                                 kernel_initializer = tf.truncated_normal_initializer(stddev=0.01, dtype=tf.float32),
                                 activation=selu.selu)

            dropout5 = selu.dropout_selu(fc5, dropoutRatePH, training=phasePH)

            Y1 = tf.layers.dense(inputs=dropout5, units=self.outputShape1[0], activation=tf.nn.sigmoid)
            Y2 = tf.layers.dense(inputs=dropout5, units=self.outputShape2[0], activation=selu.selu)
            Y3 = tf.nn.softmax(Y2)
            self.Y1 = Y1
            self.Y3 = Y3

            loss1 = tf.reduce_sum( tf.pow( Y1 - tf.slice(YPH,[0,0],[-1,self.outputShape1[0]] ), 2))
            loss2 = tf.reduce_sum( tf.nn.softmax_cross_entropy_with_logits( logits=Y2,
                                                                            labels=tf.slice( YPH, [0,self.outputShape1[0]],
                                                                                                  [-1,self.outputShape2[0]] ) ))
            loss = loss1 + loss2
            self.loss = loss

            # add summaries
            tf.summary.scalar('learning_rate', learningRatePH)
            tf.summary.scalar("loss1", loss1)
            tf.summary.scalar("loss2", loss2)
            tf.summary.scalar("loss", loss)
            for var in tf.trainable_variables():
                tf.summary.histogram(var.op.name, var)
            self.merged_summary_op = tf.summary.merge_all()

            self.training_op = tf.train.AdamOptimizer(learning_rate=learningRatePH).minimize(loss)
            self.init_op = tf.global_variables_initializer()

    def init(self):
        self.session.run( self.init_op )

    def close(self):
        self.session.close()

    def train(self, batchX, batchY):
        #for i in range(len(batchX)):
        #    tf.image.per_image_standardization(batchX[i])
        loss = 0
        loss, _, summary = self.session.run( (self.loss, self.training_op, self.merged_summary_op),
                                              feed_dict={self.XPH:batchX, self.YPH:batchY, self.learningRatePH:self.learningRateVal,
                                              self.phasePH:True, self.dropoutRatePH:self.dropoutRateVal})
        return loss, summary

    def getLoss(self, batchX, batchY):
        #for i in range(len(batchX)):
        #    tf.image.per_image_standardization(batchX[i])
        loss = 0
        loss  = self.session.run( self.loss, feed_dict={self.XPH:batchX, self.YPH:batchY, self.phasePH:False, self.dropoutRatePH:0.0})
        return loss

    def setLearningRate(self, learningRate=None):
        if learningRate == None:
            self.learningRateVal = self.learningRateVal * self.learningRateDecay
        else:
            self.learningRateVal = learningRate
        return self.learningRateVal

    def saveParameters(self, fn):
        with self.g.as_default():
            self.saver = tf.train.Saver()
            self.saver.save(self.session, fn)

    def restoreParameters(self, fn):
        with self.g.as_default():
            self.saver = tf.train.Saver()
            self.saver.restore(self.session, fn)

    def summaryFileWriter(self, logsPath):
        summaryWriter = tf.summary.FileWriter(logsPath, graph=self.g)
        return summaryWriter

    def predict(self, XArray):
        #for i in range(len(batchX)):
        #    tf.image.per_image_standardization(XArray[i])
        base, varType  = self.session.run( (self.Y1, self.Y3), feed_dict={self.XPH:XArray, self.phasePH:False, self.dropoutRatePH:0.0})
        return base, varType

    def __del__(self):
        self.session.close()
