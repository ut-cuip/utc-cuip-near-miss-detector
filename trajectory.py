from utils.utils import distance_from_bb, distance_from_xy


def predict_location(trk, amount_to_predict=2):
    """
        Predicts the future location at 'time'
        Args:
            trk (sort.KalmanBoxTracker): the tracker
            steps_backward (int): the number of locations to look previously to determine the location
    """
    current_timestamp, current_location = trk.locations[-1]
    # Return if there are less than 10 locations because of how we want this to work
    if len(trk.locations) < amount_to_predict:
        center_x = (current_location[0] + current_location[2]) / 2
        center_y = (current_location[1] + current_location[3]) / 2
        return (center_x, center_y)

    prev_timestamp, prev_hitbox = trk.locations[-amount_to_predict]
    dt = (current_timestamp - prev_timestamp) / 1000
    vel_x, vel_y = velocity(trk, steps_backward=amount_to_predict)

    pred_x = ((current_location[0] + current_location[2]) / 2) - (vel_x * dt)
    pred_y = ((current_location[1] + current_location[3]) / 2) - (vel_y * dt)
    return (pred_x, pred_y)


def velocity(trk, steps_backward=2):
    """
        Calculates the velocity of said tracker, in px/s
        Args:
            trk (sort.KalmanBoxTracker): the tracker
            steps_backward (int): the number of locations to look previously to determine the velocity
        returns:
            The speed of the tracked object
    """
    # Return 0 if there aren't enough locations
    # to be able to create velocity with
    if len(trk.locations) < steps_backward:
        return 0
    prev_timestamp, prev_hitbox = trk.locations[-steps_backward]
    current_timestamp, current_hitbox = trk.locations[-1]
    # Divide by 1000 because of how we store the unix ts
    dt = (current_timestamp - prev_timestamp) / 1000

    vel_x = (
        ((prev_hitbox[0] + prev_hitbox[2]) / 2)
        - ((current_hitbox[0] + current_hitbox[2]) / 2)
    ) / dt

    vel_y = (prev_hitbox[3] - current_hitbox[3]) / dt

    return (vel_x, vel_y)


def time_til_collision(trk1, trk2, threshold=10):
    """
        Determines if two trackers should collide
        Args:
            trk1 (sort.KalmanBoxTracker)
            trk2 (sort.KalmanBoxTracker)
        returns:
            -1 if no collision
            ttc if collision is possible
    """
    if len(trk1.locations) < threshold or len(trk2.locations) < threshold:
        return -1

    pred_trk1_pos = predict_location(trk1, amount_to_predict=threshold)
    pred_trk2_pos = predict_location(trk2, amount_to_predict=threshold)
    pred_distance = distance_from_xy(pred_trk1_pos, pred_trk2_pos)
    known_distance = distance_from_bb(trk1.locations[-1][1], trk2.locations[-1][1])

    # If distance is decreasing...
    if known_distance > pred_distance:
        ttc = 0
        while known_distance + (pred_distance - known_distance) * ttc > 0:
            ttc += 1
        return ttc
    else:
        return -1
