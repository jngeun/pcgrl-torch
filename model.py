import gym
import numpy as np

from stable_baselines3.common.policies import ActorCriticPolicy, BaseFeaturesExtractor
from stable_baselines3.common.distributions import CategoricalDistribution

import torch
import torch.nn as nn

def Cnn1(image, **kwargs):
    activ = tf.nn.relu
    layer_1 = activ(conv(image, 'c1', n_filters=32, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
    layer_2 = activ(conv(layer_1, 'c2', n_filters=64, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
    layer_3 = activ(conv(layer_2, 'c3', n_filters=64, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
    layer_3 = conv_to_fc(layer_3)
    return activ(linear(layer_3, 'fc1', n_hidden=512, init_scale=np.sqrt(2)))

def FullyConv1(image, n_tools, **kwargs):
    activ = tf.nn.relu
    x = activ(conv(image, 'c1', n_filters=32, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c2', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c3', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c4', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c5', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c6', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c7', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c8', n_filters=n_tools, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    act = conv_to_fc(x)
    val = activ(conv(x, 'v1', n_filters=64, filter_size=3, stride=2,
        init_scale=np.sqrt(2)))
    val = activ(conv(val, 'v4', n_filters=64, filter_size=1, stride=1,
        init_scale=np.sqrt(2)))
    val = conv_to_fc(val)
    return act, val

def FullyConv2(image, n_tools, **kwargs):
    activ = tf.nn.relu
    x = activ(conv(image, 'c1', n_filters=32, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c2', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c3', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c4', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c5', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c6', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c7', n_filters=64, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    x = activ(conv(x, 'c8', n_filters=n_tools, filter_size=3, stride=1,
        pad='SAME', init_scale=np.sqrt(2)))
    act = conv_to_fc(x)
    val = activ(conv(x, 'v1', n_filters=64, filter_size=3, stride=2,
        init_scale=np.sqrt(2)))
    val = activ(conv(val, 'v2', n_filters=64, filter_size=3, stride=2,
        init_scale=np.sqrt(3)))
    val = activ(conv(val, 'v4', n_filters=64, filter_size=1, stride=1,
        init_scale=np.sqrt(2)))
    val = conv_to_fc(val)
    return act, val

class NoDenseCategoricalProbabilityDistributionType(CategoricalDistribution):
    def __init__(self, n_cat):
        """
        The probability distribution type for categorical input

        :param n_cat: (int) the number of categories
        """
        self.n_cat = n_cat

    def probability_distribution_class(self):
        return CategoricalProbabilityDistribution

    def proba_distribution_from_latent(self, pi_latent_vector, vf_latent_vector, init_scale=1.0,
                                       init_bias=0.0):
        pdparam = pi_latent_vector
        q_values = vf_latent_vector
        return self.proba_distribution_from_flat(pdparam), pdparam, q_values

    def param_shape(self):
        return [self.n_cat]

    def sample_shape(self):
        return []

    def sample_dtype(self):
        return tf.int64

class FullyConvPolicyBigMap(ActorCriticPolicy):
    def __init__(self, sess, ob_space, ac_space, n_env, n_steps, n_batch, **kwargs):
        super(FullyConvPolicyBigMap, self).__init__(sess, ob_space, ac_space, n_env, n_steps, n_batch, **kwargs)
        n_tools = int(ac_space.n / (ob_space.shape[0] * ob_space.shape[1]))
        self._pdtype = NoDenseCategoricalProbabilityDistributionType(ac_space.n)
        with tf.variable_scope("model", reuse=kwargs['reuse']):
            pi_latent, vf_latent = FullyConv2(self.processed_obs, n_tools, **kwargs)
            self._value_fn = linear(vf_latent, 'vf', 1)
            self._proba_distribution, self._policy, self.q_value = \
                self.pdtype.proba_distribution_from_latent(pi_latent, vf_latent, init_scale=0.01)
        self._setup_init()

    def step(self, obs, state=None, mask=None, deterministic=False):
        if deterministic:
            action, value, neglogp = self.sess.run([self.deterministic_action, self.value_flat, self.neglogp],
                                                   {self.obs_ph: obs})
        else:
            action, value, neglogp = self.sess.run([self.action, self.value_flat, self.neglogp],
                                                   {self.obs_ph: obs})
        return action, value, self.initial_state, neglogp

    def proba_step(self, obs, state=None, mask=None):
        return self.sess.run(self.policy_proba, {self.obs_ph: obs})

    def value(self, obs, state=None, mask=None):
        return self.sess.run(self.value_flat, {self.obs_ph: obs})

class FullyConvPolicySmallMap(ActorCriticPolicy):
    def __init__(self, sess, ob_space, ac_space, n_env, n_steps, n_batch, **kwargs):
        super(FullyConvPolicySmallMap, self).__init__(sess, ob_space, ac_space, n_env, n_steps, n_batch, **kwargs)
        n_tools = int(ac_space.n / (ob_space.shape[0] * ob_space.shape[1]))
        self._pdtype = NoDenseCategoricalProbabilityDistributionType(ac_space.n)
        with tf.variable_scope("model", reuse=kwargs['reuse']):
            pi_latent, vf_latent = FullyConv1(self.processed_obs, n_tools, **kwargs)
            self._value_fn = linear(vf_latent, 'vf', 1)
            self._proba_distribution, self._policy, self.q_value = \
                self.pdtype.proba_distribution_from_latent(pi_latent, vf_latent, init_scale=0.01)
        self._setup_init()

    def step(self, obs, state=None, mask=None, deterministic=False):
        if deterministic:
            action, value, neglogp = self.sess.run([self.deterministic_action, self.value_flat, self.neglogp],
                                                   {self.obs_ph: obs})
        else:
            action, value, neglogp = self.sess.run([self.action, self.value_flat, self.neglogp],
                                                   {self.obs_ph: obs})
        return action, value, self.initial_state, neglogp

    def proba_step(self, obs, state=None, mask=None):
        return self.sess.run(self.policy_proba, {self.obs_ph: obs})

    def value(self, obs, state=None, mask=None):
        return self.sess.run(self.value_flat, {self.obs_ph: obs})

class CustomPolicyBigMap(BaseFeaturesExtractor):
    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = 512):
        super(CustomPolicyBigMap, self).__init__(observation_space, features_dim)
        n_input_channels = observation_space.shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(n_input_channels, 32, kernel_size=3, stride=2, padding=0),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=0),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=0),
            nn.ReLU(),
            nn.Flatten()
        )

        # Comput shape by doing one forward pass
        with torch.no_grad():
            # n_flatten = self.cnn(
            #     torch.as_tensor(np.transpose(observation_space.sample()[None], (0, 3, 1, 2))).float()
            # ).shape[1]
            n_flatten = self.cnn(
                torch.as_tensor(observation_space.sample()[None]).float()
            ).shape[1]
            
        self.linear = nn.Sequential(nn.Linear(n_flatten, features_dim), nn.ReLU())

    def forward(self, observations : torch.Tensor) -> torch.Tensor:
        #TODO: change method that transpose matrix
        #observations = torch.from_numpy(np.transpose(observations.numpy(), (0, 3, 1, 2)))
        return self.linear(self.cnn(observations))

class CustomPolicySmallMap(BaseFeaturesExtractor):
    def __init__(self, *args, **kwargs):
        super(CustomPolicySmallMap, self).__init__(*args, **kwargs, cnn_extractor=Cnn1, feature_extraction="cnn")

