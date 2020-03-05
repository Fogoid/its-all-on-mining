import sys
import re

#########################
### A: AGENT BEHAVIOR ###
#########################

class Observation:
    def __init__(self, utility, step):
        self.utility = utility
        self.step = step

class Agent:
    def __init__(self, options):
        # Regex to decide which type of configurations there are
        self.cycle = int(re.search(r"cycle=\w+( |\n|\r\n)", options).group(0)[len("cycle="):])
        self.decision = re.search(r"decision=\w+( |\n|\r\n)", options).group(0)[len("decision="):].strip(" \r\n")
        
        restart = re.search(r"restart=\d+( |\n||\r\n)", options)
        self.restart = 0 if restart is None else int(restart.group(0)[len("restart="):].strip(" \r\n"))

        memoryFactor = re.search(r"memory-factor=\d+\.\d+( |\n|\r\n)", options)
        self.memoryFactor = 0.0 if memoryFactor is None else float(memoryFactor.group(0)[len("memory-factor="):].strip(" \r\n"))
        
        # Dictionary where the expected utilities of each task observed is kept
        self.tasks = {}
        # list with a tuple with Observations made for each task
        self.observations = {}
        #A counter of how many taks exist
        self.numTasks = 0
        #The total gain of performing the selected tasks
        self.gain = 0
        #The last task executed
        self.lastExecuted = -1
        #The step the agent is at
        self.currentStep = 0

        self.firstTask = None

    def perceive(self, perception):
        if ("T" in  perception):
            perception = perception.split(' ')
            self.tasks[int(perception[0][1:])] = float(perception[1][len("u="):])
        
        else: # It is an observation
            utiObserved = float(perception[len("A u="):])

            if self.lastExecuted in self.observations.keys():
                self.observations[self.lastExecuted] += [Observation(utiObserved, self.currentStep)]
            else:
                self.observations[self.lastExecuted] = [Observation(utiObserved, self.currentStep)]
            
            # Calculate the new Expected Utility for the task
            eu = 0
            stepSums = 0
            for obs in self.observations[self.lastExecuted]:
                eu += (obs.step ** self.memoryFactor) * obs.utility
                stepSums += obs.step ** self.memoryFactor
            eu /= stepSums

            self.tasks[self.lastExecuted] = eu
            self.gain += utiObserved

    def decide_act(self):
        best_utility = -1
        for i in self.tasks.keys():
            if (self.tasks[i] > best_utility):
                best_utility = self.tasks[i]
                self.lastExecuted = i

        agent.currentStep += 1

    def recharge(self):
        output = "state={"
        for i in self.tasks.keys():
            output += 'T%d=' % (i) + (('%.2f,' % (self.tasks[i])) if i in self.observations.keys() else "NA,")

        return output[:-1] + '} gain=%.2f' % (self.gain)

#####################
### B: MAIN UTILS ###
#####################

line = sys.stdin.readline()
agent = Agent(line)
for line in sys.stdin:
    if line.startswith("end"): break
    elif line.startswith("TIK"): agent.decide_act()
    else: agent.perceive(line)
sys.stdout.write(agent.recharge()+'\n')
