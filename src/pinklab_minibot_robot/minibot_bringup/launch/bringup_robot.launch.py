from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown, OpaqueFunction
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, LifecycleNode
from launch.event_handlers import OnProcessExit, OnExecutionComplete, OnProcessStart
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import PathJoinSubstitution, Command, LaunchConfiguration
from launch.conditions import LaunchConfigurationEquals
import launch

import os

ARGUMENTS = [
    DeclareLaunchArgument('namespace', default_value='', description='Robot namespace'),
    DeclareLaunchArgument("prefix", default_value=""),
    DeclareLaunchArgument("lidar_model", default_value="hokuyo"),
    DeclareLaunchArgument("lidar_port_name", default_value="/dev/ttyLidar"),
    DeclareLaunchArgument("lidar_baudrate", default_value="57600"),
    DeclareLaunchArgument("robot_port_name", default_value="/dev/ttyArduino"),
    DeclareLaunchArgument("robot_baudrate", default_value="500000"),
]

def launch_setup(context, *args, **kwargs):
    namespace = LaunchConfiguration('namespace')
    namespace_str = '/' + namespace.perform(context)
    # print(namespace_str)

    remappings = [  ('/tf', 'tf'),
                    ('/tf_static', 'tf_static'),
    ]

    robot_description_content = Command([
        'xacro ',
        PathJoinSubstitution([
            FindPackageShare('minibot_description'),
            'urdf/robot.urdf.xacro',
        ]),
        ' is_sim:=', 'false',
        ' lidar_model:=', LaunchConfiguration('lidar_model'),
        ' port_name:=', LaunchConfiguration('robot_port_name'),
        ' baudrate:=', LaunchConfiguration('robot_baudrate'),
        ' prefix:=', LaunchConfiguration('prefix'),
        ' namespace:=', namespace

    ])

    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution([
            FindPackageShare('minibot_bringup'),
            "config",
            "minibot_controllers.yaml"
        ]
    )

    control_node = Node(
        namespace=namespace,                                 ################################################yjs
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            robot_description,
            robot_controllers
            ],
        output={
            "stdout": "screen",
            "stderr": "screen",
        },
        remappings=remappings,
        on_exit=Shutdown(),
    )

    upload_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory('minibot_description'),
            '/launch/upload_robot.launch.py']
        ),
        launch_arguments = {
            'namespace': namespace,
            'is_sim': 'false',
            'prefix': LaunchConfiguration('prefix'),
            'lidar_model': LaunchConfiguration('lidar_model'),
        }.items()
    )


    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             '-c', namespace_str + '/controller_manager', 'joint_state_broadcaster'],
        output='screen'
    )

    load_base_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             '-c', namespace_str + '/controller_manager', 'base_controller'],
        output='screen'
    )

    load_minibot_io_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             '-c', namespace_str + '/controller_manager', 'minibot_io_controller'],
        output='screen'
    )

    # handler1 = RegisterEventHandler(
    #     event_handler=OnProcessStart(
    #         target_action=control_node,
    #         on_start=[load_joint_state_broadcaster],
    #     )
    # )
    handler2 = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_base_controller],
        )
    )
    handler3 = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_base_controller,
            on_exit=[load_minibot_io_controller],
        )
    )

    parameter_file = LaunchConfiguration('params_file')
    ydlidar_params_declare = DeclareLaunchArgument('params_file',
                                           default_value=os.path.join(
                                               get_package_share_directory('minibot_bringup'), 'config', 'ydlidar.yaml'),
                                           description='FPath to the ROS2 parameters file to use.')
    ydlidar_driver_node = LifecycleNode(package='ydlidar_ros2_driver',
                                executable='ydlidar_ros2_driver_node',
                                name='ydlidar_ros2_driver_node',
                                output='screen',
                                emulate_tty=True,
                                parameters=[parameter_file],
                                # namespace='/',
                                namespace=namespace,
                                )

    return control_node, load_joint_state_broadcaster, handler2, handler3, upload_robot, ydlidar_params_declare, ydlidar_driver_node
    
    

def generate_launch_description():

    # Define LaunchDescription variable
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))

    # ld.add_action(control_node)
    # ld.add_action(load_joint_state_broadcaster)
    # ld.add_action(handler2)
    # ld.add_action(handler3)

    # ld.add_action(upload_robot)

    # ld.add_action(ydlidar_params_declare)
    # ld.add_action(ydlidar_driver_node)

    return ld
