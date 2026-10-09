/* UNTESTED EXAMPLE: nvcc/ptxas were NOT installed on the machine where CompilerDiff
 * was built, so this file has never been compiled by this project.
 * Try (needs CUDA Toolkit; no GPU needed just to emit PTX):
 *     nvcc -ptx examples/cuda_vector_add.cu -o vector_add.ptx
 *     ptxas --gpu-name sm_75 vector_add.ptx -o vector_add.cubin
 */
__global__ void vector_add(const int *a, const int *b, int *c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
