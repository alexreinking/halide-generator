#include <Halide.h>
using namespace Halide;

class ${NAME} : public Generator<${NAME}>
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

HALIDE_REGISTER_GENERATOR(${NAME}, ${NAME.lower()})
