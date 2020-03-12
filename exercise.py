import sys
import re
import queue

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
        self.cycle = int(re.search(r"cycle=\d+( |\n|\r\n)", options).group(0)[len("cycle="):])
        self.decision = re.search(r"decision=[\w-]+( |\n|\r\n)", options).group(0)[len("decision="):].strip(" \r\n")
        
        restart = re.search(r"restart=\d+( |\n||\r\n)", options)
        self.restart = 0 if restart is None else int(restart.group(0)[len("restart="):].strip(" \r\n"))

        memoryFactor = re.search(r"memory-factor=\d+\.\d+( |\n|\r\n)", options)
        self.memoryFactor = 0.0 if memoryFactor is None else float(memoryFactor.group(0)[len("memory-factor="):].strip(" \r\n"))
        
        agents = re.search(r"agents=[\[\{]\w\d(,\w\d)*[\}\]]( |\n|\r\n)", options)
        self.agents = ["A"] if agents is None else agents.group(0)[len("agents="):].strip("}}][{{ \r\n").split(",")

        # Dictionary where the expected utilities of each task observed is kept
        self.tasks = {}
        # list with a tuple with Observations made for each task
        self.observations = {}
        #A counter of how many taks exist
        self.numTasks = 0
        #The total gain of performing the selected tasks
        self.gain = 0
        #The last task executed
        self.preparing = -1
        #The step the agent is at
        self.currentStep = 0
        # task to which we are expecting ann observation
        self.expectedObsTasks = queue.Queue()

    def perceive(self, perception):
        if ("T" in  perception):
            perception = perception.split(' ')
            self.tasks[int(perception[0][1:])] = [float(perception[1][len("u="):]), self.restart]
        
        else: # It is an observation
            utiObserved = 0
            if "A " in perception:
                utiObserved = float(perception[len("A u="):])
            else:
                utiObserved = float(perception[len("Ax u="):])

            taskObs = self.expectedObsTasks.get()

            if taskObs in self.observations.keys():
                self.observations[taskObs] += [Observation(utiObserved, self.currentStep)]
            else:
                self.observations[taskObs] = [Observation(utiObserved, self.currentStep)]
            
            # Calculate the new Expected Utility for the task
            eu = 0
            stepSums = 0
            for obs in self.observations[taskObs]:
                eu += (obs.step ** self.memoryFactor) * obs.utility
                stepSums += obs.step ** self.memoryFactor
            eu /= stepSums

            self.tasks[taskObs][0] = eu
            self.gain += utiObserved

    def decide_act(self):
        best_utility = -1

        toExecute = -1
        for i in self.tasks.keys():
            meu = self.tasks[i][0] * (self.cycle - (self.currentStep + self.tasks[i][1]))
            if (meu > best_utility):
                best_utility = meu
                toExecute = i
        
        # TO MAKE SURE BECAUSE OF THE CASE WITH TASKS HAVING ONLY NEGATIVE UTILITIES
        if toExecute == -1:
            agent.currentStep += 1
            return

        if toExecute != self.preparing:
            if self.preparing != -1:
                self.tasks[self.preparing][1] = self.restart
            self.preparing = toExecute
            
        if self.tasks[self.preparing][1] == 0:
            for _ in self.agents:
                self.expectedObsTasks.put(self.preparing)
            
        self.tasks[self.preparing][1] -= (1 if self.tasks[self.preparing][1] > 0 else 0)
        
        agent.currentStep += 1

    def recharge(self):
        output = "state={"
        
        if len(self.agents) == 1:
            for i in self.tasks.keys():
                output += 'T%d=' % (i) + (('%.2f,' % (self.tasks[i][0])) if i in self.observations.keys() else "NA,")
        else:
            for a in self.agents:
                output += a + "={"
                for i in self.tasks.keys():
                    output += 'T%d=' % (i) + (('%.2f,' % (self.tasks[i][0])) if i in self.observations.keys() else "NA,")
                output = output[:-1] + "},"

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
