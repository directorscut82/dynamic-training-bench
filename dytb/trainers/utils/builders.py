#Copyright (C) 2017 Paolo Galeone <nessuno@nerdz.eu>
#
#This Source Code Form is subject to the terms of the Mozilla Public
#License, v. 2.0. If a copy of the MPL was not distributed with this
#file, you can obtain one at http://mozilla.org/MPL/2.0/.
#Exhibit B is not attached; this software is compatible with the
#licenses expressed under Section 1.12 of the MPL v2.
"""Utilities used by the trainers"""

import math
import os
import tensorflow as tf

from ...models.utils import variables_to_save, variables_to_restore
from ...models.visualization import on_grid


def build_optimizer(args, steps, global_step):
    """Build the specified optimizer, log the learning rate and enalble
    learning rate decay is specified.
    Args:
        args: the optimization argument dict
        global_step: integer tensor, the current training step
    Returns:
        optimizer: tf.Optimizer object initialized
    """
    # Extract the initial learning rate
    initial_lr = float(args["gd"]["args"]['learning_rate'])

    if args["lr_decay"]["enabled"]:
        # Decay the learning rate exponentially based on the number of steps.
        learning_rate = tf.train.exponential_decay(
            initial_lr,
            global_step,
            steps["decay"],
            args["lr_decay"]["factor"],
            staircase=True)
        # Update the learning rate parameter of the optimizer
        args["gd"]["args"]['learning_rate'] = learning_rate
        # Log the learning rate
        tf_log(tf.summary.scalar('learning_rate', learning_rate))
    else:
        learning_rate = tf.constant(initial_lr)

    # Instantiate the optimizer
    optimizer = args["gd"]["optimizer"](**args["gd"]["args"])
    return optimizer


def restore_or_restart(args, paths, sess, global_step):
    """Restore actual session or restart the training.
    If SESS.checkpoint_path is setted, start a new train
    loading the weight from the lastest checkpoint in that path
    Args:
        sess: session
        paths: dict of paths
        global_step: global_step tensor
    """

    # first check if exists and checkpoint_path passed
    # from where to load the weights.
    # Return error if there's not
    pretrained_checkpoint = None
    if args["checkpoint_path"] != '':
        pretrained_checkpoint = tf.train.latest_checkpoint(
            args["checkpoint_path"])
        if not pretrained_checkpoint:
            print("[E] {} not valid".format(args["checkpoint_path"]))
            sys.exit(-1)

    if not args["force_restart"]:
        # continue training checkpoint
        continue_checkpoint = tf.train.latest_checkpoint(paths["log"])
        if continue_checkpoint:
            restore_saver = build_restore_saver(
                [global_step], scopes_to_remove=args["exclude_scopes"])
            restore_saver.restore(sess, continue_checkpoint)
        # else if the continue checkpoint does not exists
        # and the pretrained checkpoint has been specified
        # load the weights from the pretrained checkpoint
        elif pretrained_checkpoint:
            restore_saver = build_restore_saver(
                [], scopes_to_remove=args["exclude_scopes"])
            restore_saver.restore(sess, pretrained_checkpoint)
        else:
            print('[I] Unable to restore from checkpoint')


def build_restore_saver(variables_to_add=[], scopes_to_remove=[]):
    """Return a saver that restores every trainable variable that's not
    under a scope to remove"""
    restore_saver = tf.train.Saver(
        variables_to_restore(variables_to_add, scopes_to_remove))
    return restore_saver


def build_train_savers(variables_to_add=[]):
    """Add variables_to_add to the collection of variables to save.
    Returns:
        train_saver: saver to use to log the training model
        best_saver: saver used to save the best model
    """
    variables = variables_to_save(variables_to_add)
    train_saver = tf.train.Saver(variables, max_to_keep=2)
    best_saver = tf.train.Saver(variables, max_to_keep=1)
    return train_saver, best_saver


def build_loggers(graph, paths):
    """Build the FileWriter object used to log summaries.
    Args:
        graph: the graph which operations to log refers to
        paths: dict of paths
    Returns:
        train_log: tf.summary.FileWriter object to log train op
        validation_log: tf.summary.FileWriter object to log validation op
    """
    train_log = tf.summary.FileWriter(
        os.path.join(paths["log"], 'train'), graph=graph)
    validation_log = tf.summary.FileWriter(
        os.path.join(paths["log"], 'validation'), graph=graph)
    return train_log, validation_log
