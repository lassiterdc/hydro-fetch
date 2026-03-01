#!/bin/bash
#SBATCH -o _script_outputs/%x/%A_out_%a_%N.out
#SBATCH -e _script_outputs/%x/%A_err_%a_%N.out
#SBATCH --ntasks=1				# Number of tasks per serial job (must be 1)
#SBATCH -p standard				# Queue name "standard" (serial)
#SBATCH -A quinnlab				# allocation name
#SBATCH -t 10:00:00				# Run time per serial job (hh:mm:ss)
#SBATCH -c 4
#SBATCH --mem=16000
#SBATCH --array=1-11,15-24			# Array of jobs to loop through (2001-2011, 2015-2022)
#SBATCH --mail-user=dcl3nd@virginia.edu          # address for email notification
#SBATCH --mail-type=ALL   

# cd /project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/scripts/hpc
# ijob -c 4 -A quinnlab -p standard --time=0-016:00:00 --mem-per-cpu=16000

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

START_YEAR=2001
YEAR=$(($START_YEAR + $SLURM_ARRAY_TASK_ID - 1))

# ${assar_dirs[hpc_da3]} ${START_YEAR} ${YEAR} ${assar_dirs[out_fullres_dailyfiles_consolidated]} ${assar_dirs[scratch_csv]} ${assar_dirs[raw_aorc]}
python ${assar_dirs[hpc_i]} ${assar_dirs[out_fullres_dailyfiles_consolidated]} ${assar_dirs[raw_aorc]} ${assar_dirs[shp_gages]} ${assar_dirs[out_fullres_yearly_atgages]} ${YEAR}

if [ "$SLURM_ARRAY_TASK_ID" -eq 1 ]; then
  echo "SLURM_ARRAY_TASK_ID=1 also tries to consolidate all mrms data into a single zarr"
  python ${assar_dirs[hpc_i]} ${assar_dirs[out_fullres_dailyfiles_consolidated]} ${assar_dirs[raw_aorc]} ${assar_dirs[shp_gages]} ${assar_dirs[out_fullres_yearly_atgages]}
fi