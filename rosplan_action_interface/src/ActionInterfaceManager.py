#!/usr/bin/env python

import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback

from BaseActionInterface import BaseActionInterface
from ActionlibActionInterface import ActionlibActionInterface
from ServiceActionInterface import ServiceActionInterface
from FSMActionInterface import FSMActionInterface
from RPKnowledgeBaseLink import RPKnowledgeBaseLink

# This class defines the action interface manager node. The node:
# - initialises a set of action interfaces according to config file;
# - subscribes to the PDDL action dispatch topic;
# - runs action execution through interfaces;
class ActionInterfaceManager(object):

    # interfaces to manage
    _action_interfaces = {}

    def __init__(self):

        # knowledge base link
        self._kb_link = RPKnowledgeBaseLink()

        # load action interfaces from configuration file
        found_config = False
        if rospy.has_param('actions'):
            self.cfg_actions = rospy.get_param('actions')
            found_config = True
        if not found_config:
            rospy.logerr('KCL: ({}) Error: configuration file was not laoded.'.format(rospy.get_name()))
            rospy.signal_shutdown('Config not found')
            return

        # feedback
        aft = rospy.get_param('~action_feedback_topic', 'default_feedback_topic')
        self._action_feedback_pub = rospy.Publisher(aft, ActionFeedback, queue_size=10)

        # subscribe to action dispatch
        adt = rospy.get_param('~action_dispatch_topic', 'default_dispatch_topic')
        rospy.Subscriber(adt, ActionDispatch, self.dispatch_callback, queue_size=10)

        self.parse_config()

        rospy.loginfo('KCL: ({}) Ready to receive'.format(rospy.get_name()))

    # PDDL action dispatch callback
    def dispatch_callback(self, pddl_action_msg):

        if not pddl_action_msg.name in self._action_interfaces:
            # manager does not handle this PDDL action
            return

        # Publish feedback: action enabled
        fb = ActionFeedback()
        fb.action_id = pddl_action_msg.action_id
        fb.plan_id = pddl_action_msg.plan_id
        fb.status = ActionFeedback.ACTION_DISPATCHED_TO_GOAL_STATE
        self._action_feedback_pub.publish(fb)

        # Set the start effects
        self._kb_link.kb_apply_action_effects(pddl_action_msg,0)

        # find and run action interface
        current_interface = self._action_interfaces[pddl_action_msg.name]
        current_interface.run(pddl_action_msg)

    #==============#
    # YAML parsing #
    #==============#

    # parse YAML config and create action interfaces
    def parse_config(self):
        for action in self.cfg_actions:
            if action["interface_type"] == "actionlib":
                self.parse_actionlib(action)
            if action["interface_type"] == "service":
                self.parse_service(action)
            if action["interface_type"] == "fsm":
                self.parse_state_machine(action)

    # base case: parse actionlib interface
    def parse_actionlib(self, action_config):
        ai = ActionlibActionInterface(action_config, None, self._action_feedback_pub)
        self._action_interfaces[ai.get_action_name()] = ai

    # base case: parse service interface
    def parse_service(self, action_config):
        ai = ServiceActionInterface(action_config, None, self._action_feedback_pub)
        self._action_interfaces[ai.get_action_name()] = ai
        pass

    # parse fsm interface
    def parse_state_machine(self, action_config):
        ai = FSMActionInterface(action_config, None, self._action_feedback_pub)
        self._action_interfaces[ai.get_action_name()] = ai


if __name__ == '__main__':
    rospy.init_node('RPStateMachine')
    aim = ActionInterfaceManager()
    rospy.spin()
