#include <Halide.h>
using namespace Halide;

class Hello : public Generator<Hello>
{
public:
	Input<Buffer<float>> input{"input", 2};
	Output<Buffer<float>> output{"output", 2};

	Var x, y;
	Func blur;

	void generate() {
		blur(x, y) = (input(x - 1, y) + input(x, y) + input(x + 1, y)) / 3.0f;
		output(x, y) = (blur(x, y - 1) + blur(x, y) + blur(x, y + 1)) / 3.0f;
	}

	void schedule() {
	}
};

HALIDE_REGISTER_GENERATOR(Hello, hello)
