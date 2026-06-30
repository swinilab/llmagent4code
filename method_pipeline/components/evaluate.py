from abc import ABC, abstractmethod
from config import Config
from concrete.evaluate.jmeter import JMeterMain

class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self) -> None:
        pass

class JMeterEvaluatorAdapter(BaseEvaluator):
    def __init__(self, config: Config):
        self.config = config
        self.jmeter = JMeterMain(self.config)

    def evaluate(self) -> None:
        print("-> [Eval] JMeter is attacking your app...")
        self.jmeter.execute_full_cycle()