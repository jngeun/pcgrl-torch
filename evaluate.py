
"""
Run a trained agent for qualitative analysis.
"""
import os
from pdb import set_trace as T
import numpy as np
import cv2
from utils import get_exp_name, max_exp_idx, load_model, get_action
from envs import make_vec_envs
from matplotlib import pyplot as plt

font                   = cv2.FONT_HERSHEY_SIMPLEX
bottomLeftCornerOfText = (10,500)
fontScale              = 1
fontColor              = (255,255,255)
lineType               = 2

def infer(game, representation, experiment, infer_kwargs, **kwargs):
    """
     - max_trials: The number of trials per evaluation.
     - infer_kwargs: Args to pass to the environment.
    """
    infer_kwargs = {
            **infer_kwargs,
            'inference': True,
            'render': True,
            'evaluate': True
            }
    max_trials = kwargs.get('max_trials', -1)
    n = kwargs.get('n', None)
    map_width = infer_kwargs.get('map_width')
    max_steps = infer_kwargs.get('max_steps')
    env_name = '{}-{}-v0'.format(game, representation)
    exp_name = get_exp_name(game, representation, experiment, **kwargs)
    if n is None:
        if EXPERIMENT_ID is None:
            n = max_exp_idx(exp_name)
        else:
            n = EXPERIMENT_ID
    if n == 0:
        raise Exception('Did not find ranked saved model of experiment: {}'.format(exp_name))
    if game == "binarygoal":
        infer_kwargs['cropped_size'] = 32
    elif game == "zeldagoal":
        infer_kwargs['cropped_size'] = 32
    elif game == "sokobangoal":
        infer_kwargs['cropped_size'] = 10
    log_dir = '{}/{}_{}_log'.format(EXPERIMENT_DIR, exp_name, n)
    data_path = os.path.join(log_dir, 'cell_scores.npy')
    if VIS_ONLY:
        cell_scores = np.load(data_path)
        visualize_data(cell_scores)
        return
    # no log dir, 1 parallel environment
    n_cpu = infer_kwargs.get('n_cpu')
    env, dummy_action_space, n_tools = make_vec_envs(env_name, representation, None, **infer_kwargs)
    model = load_model(log_dir, load_best=infer_kwargs.get('load_best'), n_tools=n_tools)
#   model.set_env(env)
    env.action_space = dummy_action_space
    # Record final values of each trial
#   if 'binary' in env_name:
#       path_lengths = []
#       changes = []
#       regions = []
#       infer_info = {
#           'path_lengths': [],
#           'changes': [],
#           'regions': [],
#           }
    if n_cpu == 1:
        control_bounds = env.envs[0].get_control_bounds()
    elif n_cpu > 1:
        env.remotes[0].send(('env_method', ('get_control_bounds', [], {})))  # supply args and kwargs
        control_bounds = env.remotes[0].recv()
    ctrl_bounds = [(k, v) for (k, v) in control_bounds.items()]
    if len(ctrl_bounds) == 1:
        ctrl_name = ctrl_bounds[0][0]
        bounds = ctrl_bounds[0][1] 
        eval_trgs = np.arange(bounds[0], bounds[1] + 1, 30)
        cell_scores = np.zeros((len(eval_trgs), 1))
        for i, trg in enumerate(eval_trgs):
            trg_dict = {ctrl_name: trg}
            print('evaluating control targets: {}'.format(trg_dict))
            env.envs[0].set_trgs(trg_dict)
#           set_ctrl_trgs(env, {ctrl_name: trg})
            rew = eval_episodes(model, env, 1, n_cpu)
            cell_scores[i] = rew
    visualize_data(cell_scores)
    np.save(data_path, cell_scores)

def visualize_data(cell_scores):
    fig, ax = plt.subplots()
    im = ax.imshow(cell_scores)
    plt.show()

def eval_episodes(model, env, n_trials, n_envs):
    eval_scores = np.zeros(n_trials)
    n = 0
    # FIXME: why do we need this?
    while n < n_trials:
        obs = env.reset()
#       epi_rewards = np.zeros((max_step, n_envs))
        i = 0
        # note that this is weighted loss
        init_loss = env.envs[0].get_loss()
        done = False
        while not done:
            action, _ = model.predict(obs)
            obs, rewards, done, info = env.step(action)
#           epi_rewards[i] = rewards
            i += 1
        final_loss = env.envs[0].get_loss()
        # what percentage of loss (distance from target) was recovered?
        score = (final_loss - init_loss) / abs(init_loss)
        eval_scores[n] = score
        n += n_envs
    eval_score = eval_scores.mean()
    print('eval score: {}'.format(eval_score))
    return eval_score


#NOTE: let's not try multiproc how about that :~)

#def eval_episodes(model, env, n_trials, n_envs):
#    eval_scores = np.zeros(n_trials)
#    n = 0
#    # FIXME: why do we need this?
#    env.reset()
#    while n < n_trials:
#
#        obs = env.reset()
##       epi_rewards = np.zeros((max_step, n_envs))
#        i = 0
##       env.remotes[0].send(('env_method', ('get_metric_vals', [], {})))  # supply args and kwargs
##       init_metric_vals = env.remotes[0].recv()
#        [remote.send(('env_method', ('get_loss', [], {}))) for remote in env.remotes]
#        # note that this is weighted loss
#        init_loss = np.sum([remote.recv() for remote in env.remotes])
#        dones = np.array([False])
#        while not dones.all():
#            action, _ = model.predict(obs)
#            T()
#            obs, rewards, dones, info = env.step(action)
##           epi_rewards[i] = rewards
#            i += 1
#        # since reward is weighted loss
#        final_loss = np.sum(rewards)
#        # what percentage of loss (distance from target) was recovered?
#        score = (final_loss - init_loss) / abs(init_loss)
##       env.remotes[0].send(('env_method', ('get_metric_vals', [], {})))  # supply args and kwargs
##       final_metric_vals = env.remotes[0].recv()
#        eval_scores[n] = score
#        n += n_envs
#    return eval_scores.mean()
#
#def set_ctrl_trgs(env, trg_dict):
#    [remote.send(('env_method', ('set_trgs', [trg_dict], {}))) for remote in env.remotes]


from arguments import get_args
args = get_args()
args.add_argument('--vis_only',
        help='Just load data from previous evaluation and visualize it.',
        action='store_true',
        )
opts = args.parse_args()
global VIS_ONLY 
VIS_ONLY = opts.vis_only

# For locating trained model
global EXPERIMENT_ID
global EXPERIMENT_DIR
#EXPERIMENT_DIR = 'hpc_runs/runs'
EXPERIMENT_DIR = 'runs'
EXPERIMENT_ID = opts.experiment_id
game = opts.problem
representation = opts.representation
conditional = True
midep_trgs = opts.midep_trgs
ca_action = opts.ca_action
if conditional:
    experiment = 'conditional'
else:
    experiment = 'vanilla'
kwargs = {
       #'change_percentage': 1,
       #'target_path': 105,
       #'n': 4, # rank of saved experiment (by default, n is max possible)
        }

if conditional:
    max_step = 1000
    cond_metrics = opts.conditionals

    if midep_trgs:
        experiment = '_'.join([experiment, 'midepTrgs'])
    if ca_action:
        experiment = '_'.join([experiment, 'CAaction'])
    experiment = '_'.join([experiment] + cond_metrics)
else:
    max_step = None
    cond_metrics = None

# For inference
infer_kwargs = {
       #'change_percentage': 1,
       #'target_path': 200,
        'conditional': True,
        'cond_metrics': cond_metrics,
        'max_step': max_step,
        'render': True,
        'n_cpu': opts.n_cpu,
        'load_best': opts.load_best,
        'midep_trgs': midep_trgs,
        'infer': True,
        'ca_action': ca_action,
        'map_width': 16
        }

if __name__ == '__main__':

    infer(game, representation, experiment, infer_kwargs, **kwargs)
#   evaluate(test_params, game, representation, experiment, infer_kwargs, **kwargs)
#   analyze()