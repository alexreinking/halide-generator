#include <Halide.h>
using namespace Halide;

class HasParam : public Generator<HasParam>
{
public:
	GeneratorParam<float> scale{"scale", 1.0f};

	Input<Buffer<float>> input{"input", 2};
	Output<Buffer<float>> output{"output", 2};

	Var x, y;

	void generate() {
		output(x, y) = scale * input(x, y);
	}

	void schedule() {
	}
};

HALIDE_REGISTER_GENERATOR(HasParam, hasparam)
