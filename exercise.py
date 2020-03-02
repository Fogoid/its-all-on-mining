import sys


#########################
### A: AGENT BEHAVIOR ###
#########################

class Agent:
    def __init__(self, options):
        pass

    def perceive(self, input):
        pass

    def decide_act(self):
        pass

    def recharge(self):
        return 'output'


#####################
### B: MAIN UTILS ###
#####################

line = sys.stdin.readline()
agent = Agent(line.split(' '))
for line in sys.stdin:
    if line.startswith("end"): break
    elif line.startswith("TIK"): agent.decide_act()
    else: agent.perceive(line)
sys.stdout.write(agent.recharge()+'\n')
