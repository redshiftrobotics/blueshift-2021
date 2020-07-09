# Setup conda to work in a bash script
eval "$(conda shell.bash hook)"

# Activate the robot controller environment and go to the correct location
conda activate robot-controller
cd ~/blueshift2020/RobotController/

# Run the Earth Node script
python EarthNode.py