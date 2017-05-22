from vector2d import Vector2D
from interpolator import Interpolator
from pwm_controller import PWMController
from utils import map_range


# Each game controller axis returns a value in the closed interval [-1, 1]. We
# limit the number of decimal places we use with the PRECISION constant. This is
# done for a few reasons: 1) it makes the numbers more human-friendly (easier to
# read) and 2) it reduces the number of thruster updates.
#
# To elaborate on this last point, I was seeing a lot of very small fluctations
# with the values coming from my PS4 controller. The change in values were so
# small, they effectively would not change the current thruster value. By
# reducing the precision, these very small fluctuations get filtered out,
# resulting in fewer thruster updates. Also, I found that when I let go of a
# joystick, the value would hover around 0.0 but would never actually become
# zero. This means the thrusters would always be active, consuming battery power
# unnecessarily. Again, by limiting the precision, these small fluctuations were
# filtered out resulting in consistent zero values when then joysticks were in
# their resting positions.
#
# Using three digits of precisions was an arbitrary choice that just happened to
# work the first time. If we find that we need more fine control of the
# thrusters, we may need to increase this value.
PRECISION = 3

# Define a series of comstants, one for each thruster
HL = 0  # horizontal left
VL = 1  # vertical left
VC = 2  # vertical center
VR = 3  # vertical right
HR = 4  # horizontal right

# Define constants for the PWM to run a thruster in full reverse, full forward,
# or neutral
FULL_REVERSE = 246
NEUTRAL = 369
FULL_FORWARD = 496


class ThrusterController:
    def __init__(self):
        # setup motor controller. The PWM controller can control up to 16
        # different devices. We have to add devices, one for each thruster that
        # we can control. The first parameter is the human-friendly name of the
        # device. That is used for logging to the console and/or a database. The
        # next parameter indicates which PWM connector this device is connected
        # to. This is refered to as the PWM channel. The last two values
        # indicate at what time intervals (ticks) the PWM should turn on and
        # off, respectively. We simply start each device at 0 time and control
        # the duration of the pulses by adjusting the off time. Note that we may
        # be able to shuffle on/off times to even out the current draw from the
        # thrusters, but so far, that hasn't been an issue. It's even possible
        # that the PWM controller may do that for us already.
        self.motor_controller = PWMController()
        self.motor_controller.add_device("HL", HL, 0, NEUTRAL)
        self.motor_controller.add_device("VL", VL, 0, NEUTRAL)
        self.motor_controller.add_device("VC", VC, 0, NEUTRAL)
        self.motor_controller.add_device("VR", VR, 0, NEUTRAL)
        self.motor_controller.add_device("HR", HR, 0, NEUTRAL)

        # setup the joysticks. We use a 2D vector to represent the x and y
        # values of the joysticks.
        self.j1 = Vector2D()
        self.j2 = Vector2D()

        # setup the various interpolators for each thruster. Each item we add
        # to the interpolator consists of two values: an angle in degrees and a
        # thrust value. An interpolator works by returning a value for any given
        # input value. More specifically in this case, we will give each
        # interpolator an angle and it will return a thrust value for that
        # angle. Since we have only given the interpolator values for very
        # specific angles, it will have to determine values for angles we have
        # not provided. It does this using linear interpolation.
        self.left_thruster = Interpolator()
        self.left_thruster.addIndexValue(0.0, -1.0)
        self.left_thruster.addIndexValue(90.0, 1.0)
        self.left_thruster.addIndexValue(180.0, 1.0)
        self.left_thruster.addIndexValue(270.0, -1.0)
        self.left_thruster.addIndexValue(360.0, -1.0)

        self.right_thruster = Interpolator()
        self.right_thruster.addIndexValue(0.0, 1.0)
        self.right_thruster.addIndexValue(90.0, 1.0)
        self.right_thruster.addIndexValue(180.0, -1.0)
        self.right_thruster.addIndexValue(270.0, -1.0)
        self.right_thruster.addIndexValue(360.0, 1.0)

        self.v_front_thruster = Interpolator()
        self.v_front_thruster.addIndexValue(0.0, 0.0)
        self.v_front_thruster.addIndexValue(90.0, -1.0)
        self.v_front_thruster.addIndexValue(180.0, 0.0)
        self.v_front_thruster.addIndexValue(270.0, 1.0)
        self.v_front_thruster.addIndexValue(360.0, 0.0)

        self.v_back_left_thruster = Interpolator()
        self.v_back_left_thruster.addIndexValue(0.0, 1.0)
        self.v_back_left_thruster.addIndexValue(90.0, 1.0)
        self.v_back_left_thruster.addIndexValue(180.0, -1.0)
        self.v_back_left_thruster.addIndexValue(270.0, -1.0)
        self.v_back_left_thruster.addIndexValue(360.0, 1.0)

        self.v_back_right_thruster = Interpolator()
        self.v_back_right_thruster.addIndexValue(0.0, -1.0)
        self.v_back_right_thruster.addIndexValue(90.0, 1.0)
        self.v_back_right_thruster.addIndexValue(180.0, 1.0)
        self.v_back_right_thruster.addIndexValue(270.0, -1.0)
        self.v_back_right_thruster.addIndexValue(360.0, -1.0)

        # setup ascent/descent controllers
        self.ascent = -1.0
        self.descent = -1.0

    def __del__(self):
        '''
        When an instance of this class gets destroyed, we need to make sure that
        we turn off all motors. Otherwise, we could end up in a situation where
        the vehicle could have thrusters running when we don't have scripts
        running to control it.
        '''
        self.set_motor(HL, 0.0)
        self.set_motor(VL, 0.0)
        self.set_motor(VC, 0.0)
        self.set_motor(VL, 0.0)
        self.set_motor(HR, 0.0)

    def update_axis(self, axis, value):
        '''
        This is the main method of this class. It is responsible for taking an
        controller input value (referred to as an axis value) and then
        converting that into the appropriate thrust values for the appropriate
        thrusters associated with that axis.

        For the two joysticks, we convert the joystick position into an angle.
        We know which thrusters each joystick controls, so we feed the
        calculated angle into the thruster interpolators for that joystick. This
        gives us the new thruster value for each thruster, which we then apply
        to the PWM controller devices for those thrusters.

        Note that the angle of the joystick does not give us all of the
        information that we need. If the joystick is close to the center
        position, then we don't need to apply as much thrust. If it is pushed
        all the way to the edge, then we nee 100% thrust. So, we treat the
        center as 0% and the edge as 100%. The values we get back from the
        interpolators are 100% values, so we simply apply the joystick
        percentage to the interpolator value to find the actual thrust value we
        need to use.

        Things get a bit more complicated for the vertical thrusters because it
        is possible that we will be pitiching or rolling the vehicle while
        simultaneously trying to move the vehicle directly up or down. If we
        pitch or roll the vehicle only, then the process is exactly as we
        described above. However, if are pithing and/or rolling AND moveing the
        vehicle vertically, we need to combine the two operations into one set
        of thruster values. We have to first determine the values for pitch and
        roll, then we increase or decrease all thruster values equally in the up
        or down direction. However it is possible that we will not be able to
        increase/decrease all thrusters by the same amount since we are already
        applying thrust for pitch and roll. This means we need to make sure our
        values do not go outside the closed intervale [-1,1]. This means that as
        we pitch or roll harder, the vehical will flattern out as we apply
        vertical thrust.
        '''

        # We need to keep track of which thrusters need updating. We use the
        # following flags for that purpose
        update_horizontal_thrusters = False
        update_vertical_thrusters = False

        # Round the incoming value to the specified precision to reduce input
        # noise
        value = round(value, PRECISION)

        # Update the appropriate joystick vector based on which controller axis
        # has changed. Note that we make sure the value is different from what
        # we have already to prevent unnecessary updates. Recall that the
        # controller may send values whose differences are smaller than our
        # precision. This means we will get an update from the controller, but
        # we decided to ignore it since it won't result in a significant change
        # to our thrusters.
        if axis == 0:
            if self.j1.x != value:
                self.j1.x = value
                update_horizontal_thrusters = True
        elif axis == 1:
            if self.j1.y != value:
                self.j1.y = value
                update_horizontal_thrusters = True
        elif axis == 2:
            if self.j2.x != value:
                self.j2.x = value
                update_vertical_thrusters = True
        elif axis == 5:
            if self.j2.y != value:
                self.j2.y = value
                update_vertical_thrusters = True
        elif axis == 3:
            if self.descent != value:
                self.descent = value
                update_vertical_thrusters = True
        elif axis == 4:
            if self.ascent != value:
                self.ascent = value
                update_vertical_thrusters = True
        else:
            pass
            # print("unknown axis ", event.axis)

        # updating horizontal thrusters is easy: find current angle, convert
        # angle to thruster values, apply values
        if update_horizontal_thrusters:
            left_value = self.left_thruster.valueAtIndex(self.j1.angle)
            right_value = self.right_thruster.valueAtIndex(self.j1.angle)
            power = min(1.0, self.j1.length)
            self.set_motor(HL, left_value * power)
            self.set_motor(HR, right_value * power)

        # updating vertical thrusters is trickier. We do the same as above, but
        # then post-process the values if we are applying vertical up/down
        # thrust. As mentioned above, we have to be careful to stay within our
        # [-1,1] interval.
        if update_vertical_thrusters:
            power = min(1.0, self.j2.length)
            back_value = self.v_front_thruster.valueAtIndex(self.j2.angle) * power
            front_left_value = self.v_back_left_thruster.valueAtIndex(self.j2.angle) * power
            front_right_value = self.v_back_right_thruster.valueAtIndex(self.j2.angle) * power
            if self.ascent != -1.0:
                percent = (1.0 + self.ascent) / 2.0
                max_thrust = max(back_value, front_left_value, front_right_value)
                max_adjust = (1.0 - max_thrust) * percent
                back_value += max_adjust
                front_left_value += max_adjust
                front_right_value += max_adjust
            elif self.descent != -1.0:
                percent = (1.0 + self.descent) / 2.0
                min_thrust = min(back_value, front_left_value, front_right_value)
                max_adjust = (min_thrust - -1.0) * percent
                back_value -= max_adjust
                front_left_value -= max_adjust
                front_right_value -= max_adjust
            self.set_motor(VC, back_value)
            self.set_motor(VL, front_left_value)
            self.set_motor(VR, front_right_value)

    def set_motor(self, motor_number, value):
        motor = self.motor_controller.devices[motor_number]
        pwm_value = int(map_range(value, -1.0, 1.0, FULL_REVERSE, FULL_FORWARD))

        # print("setting motor {0} to {1}".format(motor_number, pwm_value))
        motor.off = pwm_value


if __name__ == "__main__":
    pass
