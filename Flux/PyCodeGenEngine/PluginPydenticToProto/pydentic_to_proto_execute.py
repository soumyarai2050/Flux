from Flux.CodeGenProjects.pair_strat_engine.output.strat_manager_service_beanie_model import StratCollection, \
    OrderLimits, PortfolioLimits, PairStrat
from PyCodeGenEngine.PluginPydenticToProto.pydantic_to_proto_plugin import PydanticToProtoPlugin
from test_pydantic_class import CandleStick


if __name__ == "__main__":
    list_of_pydantic_classes = [CandleStick]
    pydantic_to_proto_plugin = PydanticToProtoPlugin(list_of_pydantic_classes, ["flux_options.proto"], "test_package")
    pydantic_to_proto_plugin.run("test1.proto")
