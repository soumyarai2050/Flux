#cd .. && exit 1 ; find . -name "*.sh" | xargs dos2unix && exit 1 ; find . -name "*.py" | xargs dos2unix && exit 1 ; export PYTHONPATH=$PWD:$PYTHONPATH && exit 1 ; cd -
cd .. ; find . -name "*.sh" | xargs dos2unix ; find . -name "*.py" | xargs dos2unix ; export PYTHONPATH=$PWD:$PYTHONPATH ; cd - ; cd Flux/CodeGenProjects ; ./add_project.sh pair_strat_engine addressbook with_model
