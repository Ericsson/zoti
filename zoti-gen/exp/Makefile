all:
	PYTHONPATH=$PYTHONPATH:../src/ python -m zoti_gen --verbose -i *.yaml -o out.c main
	clang-format -i out.c
	mv out.c ../docs/source/assets
