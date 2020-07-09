# SSH into the Water Node computer
ssh pi@169.254.92.92

# Enter the python environment and go to the correct folder
workon robot-controller
cd ~/blueshift2020/RobotController

# Start the Water Node script
python WaterNode.py