from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    

@CrewBase
class SummaryGeneratorPipeline:
    """Crew for processing natural language JIRA queries into actionable insights."""

    def __init__(self, llm):
        """
        Initializes the JiraClientPipeline.

        :param llm: Language model instance.
        """
        self.llm = llm
        logger.info("SummaryGeneratorPipeline initialized successfully.")

    @agent
    def summary_agent(self) -> Agent:
        """Creates the summary Expert agent"""
        config_key = "summary_agent"
        if config_key not in self.agents_config:
            raise KeyError(f"Missing configuration for {config_key}")
        return Agent(config=self.agents_config[config_key],llm=self.llm)

    @task
    def summary_task(self) -> Task:
        """Defines the task to process summary formation"""
        config_key = "summary_task"
        if config_key not in self.tasks_config:
            raise KeyError(f"Missing configuration for {config_key}")
        return Task(
            config=self.tasks_config[config_key]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the crew for handling Jira queries"""
        logger.info("Creating the crew for JiraClientPipeline.")
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
