#!/bin/bash
#SBATCH -o _script_outputs/%x/%A_%a_%N.out
#SBATCH -e _script_errors/%x/%A_%a_%N.out
#SBATCH --ntasks=1				# Number of tasks per serial job (must be 1)
#SBATCH -p standard				# Queue name "standard" (serial)
#SBATCH -A quinnlab				# allocation name
#SBATCH -t 24:00:00				# Run time per serial job (hh:mm:ss)
#SBATCH --array=1-3			#  1-3 (currently doing 3 groupings)
#SBATCH --mem-per-cpu=32000
#SBATCH --mail-user=dcl3nd@virginia.edu          # address for email notification
#SBATCH --mail-type=ALL   

# cd /project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/scripts/hpc
# ijob -c 1 -A quinnlab -p standard --time=0-08:00:00 --mem-per-cpu=32000

# created a new environment for this script due to a weird error

module purge
source __directories.sh
source __utils.sh

dir_outs=_script_outputs/
mkdir -p ${dir_outs}${SLURM_JOB_NAME}
archive_previous_script_outfiles

module load gcc openmpi eccodes miniforge
DIR=~/.conda/envs/mrms_processing
source activate mrms_processing
export PATH=$DIR/bin:$PATH
export LD_LIBRARY_PATH=$DIR/lib:$PATH
export PYTHONPATH=$DIR/lib/python3.11/site-packages:$PATH

python ${assar_dirs[hpc_da3b]} ${assar_dirs[out_fullres_dailyfiles_consolidated]} ${SLURM_ARRAY_TASK_ID}
# python ${assar_dirs[hpc_da3b]} ${assar_dirs[out_fullres_dailyfiles_consolidated]} 0