#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import OrderedDict
import logging
import numpy
import theano
import theano.tensor as tensor
from theanolm.matrixfunctions import random_weight, orthogonal_weight

class BasicLayer(object):
    """Superclass for Neural Network Layers
    """

    def __init__(self, layer_name, input_layers, output_size, profile=False,
                 is_recurrent=False):
        """Saves some attributes that are common to all layers.

        :type layer_name: str
        :param layer_name: name of the layer, used for prefixing parameter names

        :type input_layer: list of BasicLayers
        :param input_layer: list of layers providing input to this layer

        :type output_size: int
        :param output_size: number of output connections

        :type profile: bool
        :param profile: if set to True, creates a Theano profile object

        :type is_recurrent: bool
        :param is_recurrent: should be set to True for recurrent layers, causing
                             the hidden state from the previous time step to be
                             passed to create_structure() when creating text
                             sampler architecture
        """

        self.name = layer_name
        self.input_layers = input_layers
        self.output_size = output_size
        self.is_recurrent = is_recurrent
        self._profile = profile

        logging.debug("- %s name=%s inputs=[%s] size=%d",
            self.__class__.__name__,
            layer_name,
            ', '.join([x.name for x in input_layers]),
            self.output_size)

        self.param_init_values = OrderedDict()

    def set_params(self, params):
        self._params = params

    def _get_param(self, param_name):
        return self._params[self.name + '.' + param_name]

    def _init_random_weight(self, param_name, input_size, output_size, scale=None, count=1):
        """Generates a weight matrix from “standard normal” distribution.

        :type input_size: int
        :param input_size: size of the input dimension of the weight

        :type output_size: int
        :param output_size: size of the output dimension of the weight

        :type scale: float
        :param scale: if other than None, the matrix will be scaled by this factor

        :rtype: numpy.ndarray
        :returns: the generated weight matrix
        """

        self.param_init_values[self.name + '.' + param_name] = \
            numpy.concatenate([random_weight(input_size, output_size, scale=0.01)
                               for _ in range(count)],
                              axis=1)

    def _init_orthogonal_weight(self, param_name, input_size, output_size, scale=None, count=1):
        """Generates a weight matrix from “standard normal” distribution. If
        in_size matches out_size, generates an orthogonal matrix.

        :type input_size: int
        :param input_size: size of the input dimension of the weight

        :type output_size: int
        :param output_size: size of the output dimension of the weight

        :type scale: float
        :param scale: if other than None, the matrix will be scaled by this factor,
                      unless an orthogonal matrix is created
        """

        self.param_init_values[self.name + '.' + param_name] = \
            numpy.concatenate([orthogonal_weight(input_size, output_size, scale=0.01)
                               for _ in range(count)],
                              axis=1)

    def _init_bias(self, param_name, size, value=None):
        """Initializes a bias vector with given value.

        If ``value`` is not given, initializes the vector with zero value. If
        ``value``is a list, creates a concatenation of as many vectors as there
        are elements in the list.

        :type param_name: str
        :param param_name: name for the parameter within the layer object; the
                           actual name of the Theano shared variable will be
                           ``<layer name>.<parameter name>``.

        :type size: int
        :param size: number of elements in the vector (or in one subvector, in
                     case ``value`` is a list)

        :type value: float or list of floats
        :param value: the value to initialize the elements to, or a list of
                      values to create a concatenation of vectors
        """

        values = value if isinstance(value, list) else [value]
        subvectors = []
        for subvector_value in values:
            if subvector_value is None:
                subvector = numpy.zeros(size).astype(theano.config.floatX)
            else:
                subvector = numpy.empty(size).astype(theano.config.floatX)
                subvector.fill(subvector_value)
            subvectors.append(subvector)
        self.param_init_values[self.name + '.' + param_name] = \
            numpy.concatenate(subvectors)

    def _tensor_preact(self, input_matrix, param_name):
        weight = self._params[self.name + '.' + param_name + '.W']
        bias = self._params[self.name + '.' + param_name + '.b']
        return tensor.dot(input_matrix, weight) + bias