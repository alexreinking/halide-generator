#include <Halide.h>
using namespace Halide;

class ${NAME.title().replace('_', '')} : public Generator<${NAME.title().replace('_', '')}>
{
public:
	Input<Buffer<float>> input{"input", 2};
	Output<Buffer<float>> output{"output", 2};

	Var x, y;

	void generate() {
		output(x, y) = input(x, y);
	}

	void schedule() {
	}
};

HALIDE_REGISTER_GENERATOR(${NAME.title().replace('_', '')}, ${NAME})
