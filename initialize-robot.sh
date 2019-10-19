eval "$(conda shell.bash hook)"
conda activate robot-controller
# python --version
cd ~/blueshift2020/RobotController/
python EarthNode.py &
ssh pi@169.254.210.218 #workon robot-controller; cd ~/blueshift2020/RobotController; python WaterNode.py