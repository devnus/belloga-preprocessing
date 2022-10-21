from kafka import KafkaConsumer
from json import loads
from craft_text_detector import Craft
import os
import time
import json
from collections import OrderedDict

from kafka import KafkaProducer
from json import dumps
import time


#generator declare
def boundingbox_json_generator(produce_info_array) :
    f = open("./outputs/image_text_detection.txt", 'r')
    lines = f.readlines()
    
    bounding_box_info_array = []
    for line in lines:
        coordinate = line.strip()
        coordinate_array =list(map(int, coordinate.split(',')))
        x_info = coordinate_array[0::2]
        y_info = coordinate_array[1::2]

        bounding_box_info = OrderedDict()
        bounding_box_info["x"]=x_info
        bounding_box_info["y"]=y_info

        bounding_box_info_array.append(bounding_box_info)
    f.close()

    output_json = OrderedDict()

    output_json['enterpriseId']= produce_info_array[0]
    output_json['rawDataId']= produce_info_array[1]
    output_json['fileUrl']= produce_info_array[2]
    output_json['projectId'] = produce_info_array[3]
    output_json['fileName']= produce_info_array[4]
    
    output_json['dataType']= "OCR"
    output_json['boundingBoxInfo']= bounding_box_info_array


    output_json = json.dumps(output_json, ensure_ascii=False)
    
    
    return output_json


#producing boundingbox declare
def produce_boundingbox(output_json):
    #producer를 할당한다
    producer = KafkaProducer(acks=0, compression_type='gzip', bootstrap_servers=['13.209.250.13:9092'],
                             value_serializer=lambda x: dumps(x).encode('utf-8'))

    #data-preprocessing을 토픽으로 지정하여 데이터를 전송한다
    start = time.time()
    for i in range(1):
        preprocessed_data = json.loads(output_json)
        data = preprocessed_data
        print("Produced Data")
        print(data)
        producer.send("ocr-data-preprocessing", value=data)
        producer.flush()
        

#img preprocessing 
def image_preprocessing(message): 
    
    msg_value = message.value.decode('utf-8')
    msg_json = json.loads(msg_value)
    
        
    # 다운받을 이미지 url
    url = msg_json['fileUrl']
    # curl 요청
    os.system("curl " + url + " > labelingTarget.jpg")

    #input json을 받아서 각 변수에 담아준다
    enterpriseId = msg_json['enterpriseId']
    rawDataId = msg_json['rawDataId']
    projectId = msg_json['projectId']
    fileName = msg_json['fileName']
    imageUrl = url
    
    # set image path and export folder directory
    image = './labelingTarget.jpg' # can be filepath, PIL image or numpy array
    output_dir = 'outputs/'
    
    # create a craft instance
    craft = Craft(output_dir=output_dir, crop_type="poly", cuda=False)
    
    # apply craft text detection and export detected regions to output directory
    prediction_result = craft.detect_text(image)
    
    # unload models from ram/gpu
    craft.unload_craftnet_model()
    craft.unload_refinenet_model()
    
    # import craft functions
    from craft_text_detector import (
    read_image,
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    export_detected_regions,
    export_extra_results,
    empty_cuda_cache
    )
    
    # read image
    image = read_image(image)
    
    # load models
    refine_net = load_refinenet_model(cuda=False)
    craft_net = load_craftnet_model(cuda=False)
    
    # perform prediction
    prediction_result = get_prediction(
    image=image,
    craft_net=craft_net,
    refine_net=refine_net,
    text_threshold=0.7,
    link_threshold=0.4,
    low_text=0.4,
    cuda=False,
    long_size=1280
    )
    
    # export detected text regions
    exported_file_paths = export_detected_regions(
    image=image,
    regions=prediction_result["boxes"],
    output_dir=output_dir,
    rectify=True
    )
    
    
    
    # export heatmap, detection points, box visualization
    export_extra_results(
    image=image,
    regions=prediction_result["boxes"],
    heatmaps=prediction_result["heatmaps"],
    output_dir=output_dir
    )
    
    # unload models from gpu
    empty_cuda_cache()
    
    producer_info_array = [enterpriseId, rawDataId, imageUrl, projectId, fileName]
    return producer_info_array



# topic, broker list
consumer = KafkaConsumer('raw-data-upload', 
                         bootstrap_servers='13.209.250.13:9092',
                         enable_auto_commit=True, 
                         auto_offset_reset='earliest')

# consumer list를 가져온다
print('[begin] Preprocessing Start')
for message in consumer:
    print("Recived Data")
    print("Topic: {}, Partition: {}, Offset: {}, Key: {}, Value: {}".format( message.topic, message.partition, message.offset, message.key, message.value.decode('utf-8')))
    produce_info_array = image_preprocessing(message)
    output_json = boundingbox_json_generator(produce_info_array)
    produce_boundingbox(output_json)