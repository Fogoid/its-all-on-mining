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
        
        agents = re.search(r"agents=\[\w\d(,\w\d)*\]( |\n|\r\n)", options)
        self.agents = None if agents is None else agents.group(0)[len("agents="):].strip(" \r\n")

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
        p = perception.split(' ')
        if ("T" in  perception):
            self.tasks[int(p[0][1:])] = [float(p[1][len("u="):]), self.restart]
        
        else: # It is an observation
            utiObserved = float(p[1][len("u="):])

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

            return utiObserved

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
            self.currentStep += 1
            return -1, -1

        if toExecute != self.preparing:
            if self.preparing != -1:
                self.tasks[self.preparing][1] = self.restart
            self.preparing = toExecute
        
        
        if self.tasks[self.preparing][1] == 0:
            self.expectedObsTasks.put(self.preparing)
        
        prepTime = self.tasks[self.preparing][1]
        self.tasks[self.preparing][1] -= (1 if self.tasks[self.preparing][1] > 0 else 0)
        
        self.currentStep += 1

        return self.preparing, prepTime

    def recharge(self):
        output = "state={"
        for i in self.tasks.keys():
            output += 'T%d=' % (i) + (('%.2f,' % (self.tasks[i][0])) if i in self.observations.keys() else "NA,")

        return output[:-1] + '} gain=%.2f' % (self.gain)

class MultiAgent:

    def __init__(self, options):
        self.decision = re.search(r"decision=[\w-]+( |\n|\r\n)", options).group(0)[len("decision="):].strip(" \r\n")
        
        restart = re.search(r"restart=\d+( |\n||\r\n)", options)
        self.restart = 0 if restart is None else int(restart.group(0)[len("restart="):].strip(" \r\n"))
        
        memoryFactor = re.search(r"memory-factor=\d+\.\d+( |\n|\r\n)", options)
        self.memoryFactor = 0.0 if memoryFactor is None else float(memoryFactor.group(0)[len("memory-factor="):].strip(" \r\n"))

        self.currentStep = 0
        self.gain = 0.0
        
        agents = re.search(r"agents=[\[\{]\w\d(,\w\d)*[\}\]]( |\n|\r\n)", options)
        self.agentsNames = agents.group(0)[len("agents="):].strip("}}][{{ \r\n").split(",")
        self.agents = {}
        for a in self.agentsNames:
            self.agents[a] = Agent(options)
        self.expectedObsTasks = queue.Queue()

        if self.decision == "homogeneous-society":
            self.observations = {}

            for a in self.agents.keys():
                self.agents[a].observations = self.observations

    def perceive(self, perception):
        p = perception.split(' ')
        if ("T" in perception): #GIVE THE NEW TASK TO ALL THE AGENTS
            for a in self.agentsNames:
                self.agents[a].tasks[int(p[0][1:])] = [float(p[1][len("u="):]), self.restart]
        else:
            task = self.expectedObsTasks.get()
            if self.decision == "homogeneous-society": #GIVE THE OBSERVATION TO ALL THE AGENTS
                self.agents[p[0]].expectedObsTasks.get()
                self.addObservation(task, float(p[1][len("u="):]))
            else: #JUST GIVE TO THE CORRESPONDANT AGENT
                self.gain += self.agents[p[0]].perceive(perception)

    def decide_act(self):
        for a in self.agentsNames:
            task, timeToExecute = self.agents[a].decide_act()
            if timeToExecute == 0:
                self.expectedObsTasks.put(task) # add to queue of observations
        
        self.currentStep += 1

    def addObservation(self, task, observation):
        if task in self.observations.keys():
            self.observations[task] += [Observation(observation, self.currentStep)]
        else:
            self.observations[task] = [Observation(observation, self.currentStep)]
        
        # Calculate the new Expected Utility for the task
        eu = 0
        stepSums = 0
        for obs in self.observations[task]:
            eu += (obs.step ** self.memoryFactor) * obs.utility
            stepSums += obs.step ** self.memoryFactor
        eu /= stepSums

        for a in self.agents:
            self.agents[a].tasks[task][0] = eu
        self.gain += observation

    def recharge(self):
        output = "state={"
        for a in self.agentsNames:
            agentOutput = a + "={"
            for i in self.agents[a].tasks.keys():
                agentOutput += 'T%d=' % (i) + (('%.2f,' % (self.agents[a].tasks[i][0])) if i in self.agents[a].observations.keys() else "NA,")
            output += agentOutput[:-1] + "},"
        return output[:-1] + '} gain=%.2f' % (self.gain)
    

#####################
### B: MAIN UTILS ###
#####################

line = sys.stdin.readline()
agent = Agent(line) if "agents" not in line else MultiAgent(line)
for line in sys.stdin:
    if line.startswith("end"): break
    elif line.startswith("TIK"): agent.decide_act()
    else: agent.perceive(line)
sys.stdout.write(agent.recharge()+'\n')
