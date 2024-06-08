"""
Authors's Implementation of Twin Delayed Deep Deterministic Policy Gradients (TD3)
Paper: https://arxiv.org/abs/1802.09477
Code adapted from: https://github.com/sfujim/TD3
"""

import numpy as np
import torch
import gym
import argparse
import os
import pickle

import gym_forestfire.agents.utils as utils
import gym_forestfire.agents.td3 as td3


# Runs policy for X episodes and returns average reward
# A fixed seed is used for the eval environment
def eval_policy(policy, env_name, seed, eval_episodes=3):
    eval_env = gym.make(env_name)
    eval_env.seed(seed + 100)

    avg_reward = 0.0
    for i in range(eval_episodes):
        state, done = eval_env.reset(), False

        while not done:
            action = policy.select_action(np.array(state))
            state, reward, done, _ , _ = eval_env.step(action)
            avg_reward += reward
            if i == 0:
                eval_env.render(i)


    avg_reward /= eval_episodes
    print("---------------------------------------")
    print(f"Evaluation over {eval_episodes} episodes: {avg_reward:.3f}")
    print("---------------------------------------")
    return avg_reward


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="TD3", help="Policy name (TD3)")
    parser.add_argument(
        "--cnn",
        default=True,
        action="store_true",
        help="Wether to use CNN with the RL agent.",
    )
    parser.add_argument(
        "--env",
        default="gym_forestfire:ForestFire-v0",
        help="OpenAI gym environment name or Forest Fire environment",
    )
    parser.add_argument(
        "--seed", default=25, type=int, help="Sets Gym, PyTorch and Numpy seeds"
    )
    parser.add_argument(
        "--start_episode",
        default=100,
        type=int,
        help="Time steps initial random policy is used",
    )
    parser.add_argument(
        "--eval_freq", default=10, type=int, help="How often (episodes) we evaluate"
    )
    parser.add_argument(
        "--max_timesteps",
        default=1e8,
        type=int,
        help="Max time steps to run environment",
    )

    parser.add_argument(
        "--expl_noise", default=0.15, help="Std of Gaussian exploration noise"
    )
    parser.add_argument(
        "--batch_size",
        default=100,
        type=int,
        help="Batch size for both actor and critic",
    )
    parser.add_argument(
        "--discount",
        default=0.99,
        help="Discount factor"
        )
    parser.add_argument(
        "--tau",
        default=0.005,
        help="Target network update rate")
    parser.add_argument(
        "--policy_noise",
        default=0.2,
        help="Noise added to target policy during critic update",
    )
    parser.add_argument(
        "--noise_clip", default=0.5, help="Range to clip target policy noise"
    )
    parser.add_argument(
        "--policy_freq", default=4, type=int, help="Frequency of delayed policy updates"
    )
    parser.add_argument(
        "--train_freq",
        default=2,
        type=int,
        help="Frequency of actor and critic updates",
    )
    parser.add_argument(
        "--save_model", action="store_true", help="Save model and optimizer parameters"
    )
    parser.add_argument(
        "--load_model",
        default="7-6",
        help='Model load file name, "" doesn\'t load, "default" uses file_name',
    )
    parser.add_argument("--exp_name", default="test", help="Exp name for file names.")
    args = parser.parse_args()

    file_name = f"{args.policy}_{args.env}_{args.seed}_{args.exp_name}"
    print("---------------------------------------")
    print(f"Policy: {args.policy}, Env: {args.env}, Seed: {args.seed}")
    print("---------------------------------------")

    if not os.path.exists("./results"):
        os.makedirs("./results")

    if args.save_model and not os.path.exists("./models"):
        os.makedirs("./models")

    env = gym.make(args.env)

    # Set seeds
    env.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = float(env.action_space.high[0])
    image_obs = len(env.observation_space.shape) > 1

    kwargs = {
        "state_dim": state_dim,
        "action_dim": action_dim,
        "max_action": max_action,
        "image_obs": image_obs,
        "discount": args.discount,
        "tau": args.tau,
        "cnn": args.cnn,
    }

    # Initialize policy
    if args.policy == "TD3":
        # Target policy smoothing is scaled wrt the action scale
        kwargs["policy_noise"] = args.policy_noise * max_action
        kwargs["noise_clip"] = args.noise_clip * max_action
        kwargs["policy_freq"] = args.policy_freq
        policy = td3.TD3(**kwargs)
    else:
        exit("The {} algorithm is not implemented.".format(args.policy))

    if args.load_model != "":
        print(f"Loading model\n\n\n\n\n\n\n\n\n\n")
        if os.path.exists(f"./models/{args.load_model}.pkl"):
            with open(f"./models/{args.load_model}.pkl", "rb") as f:
                policy = pickle.load(f)
                print(f"Model loaded from ./models/{args.load_model}.pkl")

    replay_buffer = utils.ReplayBuffer(state_dim, action_dim, image_obs=image_obs)

    # Evaluate untrained policy
    # evaluations = [eval_policy(policy, args.env, args.seed)]

    state, done = env.reset(), False
    episode_reward = 0
    episode_timesteps = 0
    episode_num = 0
    result = []



    for t in range(int(args.max_timesteps)):

        episode_timesteps += 1

        # Select action randomly or according to policy

        if episode_num < args.start_episode:
            action = env.action_space.sample()
        else:
            action = (
                    policy.select_action(np.array(state))
                    + np.random.normal(0, max_action * args.expl_noise, size=action_dim)
                ).clip(-max_action, max_action)

        # Perform action
        next_state, reward, done, num_trees, _  = env.step(action)
            
        if episode_num in range(args.start_episode, args.start_episode+100, 10):
            env.render(episode_num)


        env.spec.max_episode_steps = 1000
        done_bool = float(done) if episode_timesteps < env.spec.max_episode_steps else 0
        # Store data in replay buffer
        replay_buffer.add(state, action, next_state, reward, done_bool)

        state = next_state
        episode_reward += reward

        # Train agent after collecting sufficient data
        if episode_num >= args.start_episode:
        # and episode_num % args.train_freq == 0:
            policy.train(replay_buffer, args.batch_size)

        if done:
            # +1 to account for 0 indexing. +0 on ep_timesteps since it will increment +1 even if done=True
            print(f"Total T: {t + 1} Episode Num: {episode_num + 1} Episode T: {episode_timesteps} Reward: {episode_reward:.3f} Trees: {num_trees}")
            result.append(episode_reward)
            #write results only every 5 episodes
            with open(f"./results/{args.load_model}.txt", "a") as f:
                f.write(f"{episode_reward}, {episode_timesteps}, {num_trees}\n")

            # Reset environment
            state, done = env.reset(), False
            episode_reward = 0
            episode_timesteps = 0
            episode_num += 1

        # Evaluate episode
        if (episode_num + 1) % args.eval_freq == 0 and episode_num > args.start_episode:
            evaluations = (eval_policy(policy, args.env, args.seed))
            with open(f"./results/{args.load_model}.txt", "a") as f:
                f.write(f"Evaluation: {evaluations}\n")
            evaluations = []
            
            args.save_model = True
            if args.save_model:
                print("Saving model")
                with open(f"./models/{args.load_model}.pkl", "wb") as f:
                    pickle.dump(policy, f)

            episode_num += 1

