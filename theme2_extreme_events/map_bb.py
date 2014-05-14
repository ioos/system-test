def get_coordinates(bounding_box,bounding_box_type):
    #create bounding box coordinates for the map
    coordinates = []
    if bounding_box_type is "box":
        coordinates.append([bounding_box[0][1],bounding_box[0][0]])
        coordinates.append([bounding_box[0][1],bounding_box[1][0]])
        coordinates.append([bounding_box[1][1],bounding_box[1][0]])
        coordinates.append([bounding_box[1][1],bounding_box[0][0]])
        coordinates.append([bounding_box[0][1],bounding_box[0][0]])
        return coordinates