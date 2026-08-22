# pip install azure-cognitiveservices-vision-customvision msrest

import os, time, uuid, logging
from dotenv import load_dotenv
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
from msrest.authentication import ApiKeyCredentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# ── Credentials from .env ─────────────────────────────────────────────────────
TRAINING_ENDPOINT      = os.getenv("CUSTOM_VISION_TRAINING_ENDPOINT")
training_key           = os.getenv("CUSTOM_VISION_TRAINING_KEY")
PREDICTION_ENDPOINT    = os.getenv("CUSTOM_VISION_PREDICTION_ENDPOINT")
prediction_key         = os.getenv("CUSTOM_VISION_PREDICTION_KEY")
prediction_resource_id = os.getenv("CUSTOM_VISION_PREDICTION_RESOURCE_ID")  

publish_iteration_name = "classifyModeltdai"
project_name = "darren-week6-classification"



# ── Clients — each pointed at its own separate Azure resource ─────────────────
training_credentials   = ApiKeyCredentials(in_headers={"Training-key": training_key})
prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})

with CustomVisionTrainingClient(TRAINING_ENDPOINT, training_credentials) as trainer, \
     CustomVisionPredictionClient(PREDICTION_ENDPOINT, prediction_credentials) as predictor:

    # ── Clean up only this student's previous project ─────────────────────────
    # The Custom Vision resource is shared with the class. Never delete projects
    # owned by other students.
    for project in trainer.get_projects():
        if project.name == project_name:
            for iteration in trainer.get_iterations(project.id):
                if iteration.publish_name:
                    trainer.unpublish_iteration(project.id, iteration.id)
            trainer.delete_project(project.id)
            logger.info("Deleted previous Darren project: %s", project.name)

    # ── Create a new project ──────────────────────────────────────────────────
    logger.info("Creating project: %s", project_name)

    project = trainer.create_project(project_name)

    # ── Create tags ───────────────────────────────────────────────────────────
    hemlock_tag = trainer.create_tag(project.id, "Hemlock")
    cherry_tag  = trainer.create_tag(project.id, "Japanese Cherry")

    # ── Upload images ─────────────────────────────────────────────────────────
    base_image_location = os.path.join(os.path.dirname(__file__), "Images")
    logger.info("Uploading training images...")

    image_list = []

    for image_num in range(1, 11):
        file_name = f"hemlock_{image_num}.jpg"
        with open(os.path.join(base_image_location, "Hemlock", file_name), "rb") as f:
            image_list.append(
                ImageFileCreateEntry(name=file_name, contents=f.read(), tag_ids=[hemlock_tag.id])
            )

    for image_num in range(1, 11):
        file_name = f"japanese_cherry_{image_num}.jpg"
        with open(os.path.join(base_image_location, "Japanese_Cherry", file_name), "rb") as f:
            image_list.append(
                ImageFileCreateEntry(name=file_name, contents=f.read(), tag_ids=[cherry_tag.id])
            )

    upload_result = trainer.create_images_from_files(
        project.id, ImageFileCreateBatch(images=image_list)
    )
    if not upload_result.is_batch_successful:
        logger.error("Image batch upload failed.")
        for image in upload_result.images:
            logger.error("  Image status: %s", image.status)
        raise SystemExit(1)

    # ── Train ─────────────────────────────────────────────────────────────────
    logger.info("Training model...")
    iteration = trainer.train_project(project.id)
    while iteration.status != "Completed":
        iteration = trainer.get_iteration(project.id, iteration.id)
        logger.info("Training status: %s — waiting 10 s...", iteration.status)
        time.sleep(10)

    # ── Publish iteration to the prediction resource ──────────────────────────
    trainer.publish_iteration(project.id, iteration.id, publish_iteration_name, prediction_resource_id)
    logger.info("Iteration published. Running test prediction...")

    # ── Predict (uses the separate Prediction resource endpoint) ──────────────
    test_image_path = os.path.join(base_image_location, "Test", "test_image.jpg")
    with open(test_image_path, "rb") as image_contents:
        results = predictor.classify_image(project.id, publish_iteration_name, image_contents.read())

    for prediction in results.predictions:
        print(f"  {prediction.tag_name}: {prediction.probability * 100:.2f}%")