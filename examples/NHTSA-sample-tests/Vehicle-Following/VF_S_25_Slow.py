#!/usr/bin/env python3
#
# Copyright (c) 2019 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

# See VF_C_25_Slow for a commented script

import os
import lgsvl
import sys
import time
import evaluator

MAX_EGO_SPEED = 11.18 # (40 km/h, 25 mph)
SPEED_VARIANCE = 10 # Simple Physics does not return an accurate value
MAX_POV_SPEED = 8.94 # (32 km/h, 20 mph)
MAX_POV_ROTATION = 5 #deg/s
TIME_LIMIT = 30 # seconds
TIME_DELAY = 3
MAX_FOLLOWING_DISTANCE = 50 # Apollo 3.5 is very cautious

print("VF_S_25_Slow - ", end = '')

sim = lgsvl.Simulator(os.environ.get("SIMULATOR_HOST", "127.0.0.1"), 8181)
if sim.current_scene == "SingleLaneRoad":
    sim.reset()
else:
    sim.load("SingleLaneRoad")

# sim.set_time_of_day(12)
# spawn EGO in the 2nd to right lane
egoState = lgsvl.AgentState()
egoState.transform = sim.get_spawn()[0]
ego = sim.add_agent("Jaguar2015XE (Apollo 3.5)", lgsvl.AgentType.EGO, egoState)
egoX = ego.state.position.x
egoY = ego.state.position.y
egoZ = ego.state.position.z

ego.connect_bridge(os.environ.get("BRIDGE_HOST", "127.0.0.1"), 9090)

POVState = lgsvl.AgentState()
POVState.transform = sim.map_point_on_lane(lgsvl.Vector(egoX, egoY, egoZ + 30))
POV = sim.add_agent("Sedan", lgsvl.AgentType.NPC, POVState)

def on_collision(agent1, agent2, contact):
    raise evaluator.TestException("Ego collided with {}".format(agent2))

ego.on_collision(on_collision)
POV.on_collision(on_collision)

try:
    t0 = time.time()
    sim.run(TIME_DELAY) # The EGO should start moving first
    POV.follow_closest_lane(True, MAX_POV_SPEED, False)

    while True:
        sim.run(0.5)

        egoCurrentState = ego.state
        if egoCurrentState.speed > MAX_EGO_SPEED + SPEED_VARIANCE:
            raise evaluator.TestException("Ego speed exceeded limit, {} > {} m/s".format(egoCurrentState.speed, MAX_EGO_SPEED + SPEED_VARIANCE))

        POVCurrentState = POV.state
        if POVCurrentState.speed > MAX_POV_SPEED + SPEED_VARIANCE:
            raise evaluator.TestException("POV speed exceeded limit, {} > {} m/s".format(POVCurrentState.speed, MAX_POV_SPEED + SPEED_VARIANCE))
        if POVCurrentState.angular_velocity.y > MAX_POV_ROTATION:
            raise evaluator.TestException("POV angular rotation exceeded limit, {} > {} deg/s".format(POVCurrentState.angular_velocity, MAX_POV_ROTATION))

        if evaluator.separation(POVCurrentState.position, lgsvl.Vector(1.8, 0, 125)) < 5:
            break

        if time.time() - t0 > TIME_LIMIT:
            break
except evaluator.TestException as e:
    print("FAILED: " + repr(e))
    exit()

separation = evaluator.separation(egoCurrentState.position, POVCurrentState.position)
if separation > MAX_FOLLOWING_DISTANCE:
    print("FAILED: EGO following distance was not maintained, {} > {}".format(separation, MAX_FOLLOWING_DISTANCE))
else:
    print("PASSED")