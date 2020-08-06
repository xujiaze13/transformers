import importlib
import inspect
import os
import re


# All paths are set with the intent you should run this script from the root of the repo with the command
# python utils/check_repo.py
PATH_TO_TRANSFORMERS = "src/transformers"
PATH_TO_TESTS = "tests"
PATH_TO_DOC = "docs/source/model_doc"

# Update this list for models that are not tested with a comment explaining the reason it should not be.
# Being in this list is an exception and should **not** be the rule.
IGNORE_NON_TESTED = [
    "BertLMHeadModel",  # Needs to be setup as decoder.
    "DPREncoder",  # Building part of bigger (tested) model.
    "DPRSpanPredictor",  # Building part of bigger (tested) model.
    "ReformerForMaskedLM",  # Needs to be setup as decoder.
    "T5Stack",  # Building part of bigger (tested) model.
    "TFAlbertForMultipleChoice",  # TODO: fix
    "TFAlbertForTokenClassification",  # TODO: fix
    "TFBertLMHeadModel",  # TODO: fix
    "TFElectraForMultipleChoice",  # Fix is in #6284
    "TFElectraForQuestionAnswering",  # TODO: fix
    "TFElectraForSequenceClassification",  # Fix is in #6284
    "TFElectraMainLayer",  # Building part of bigger (tested) model (should it be a TFPreTrainedModel ?)
    "TFRobertaForMultipleChoice",  # TODO: fix
]

# Update this list with test files that don't have a tester with a `all_model_classes` variable and which don't
# trigger the common tests.
TEST_FILES_WITH_NO_COMMON_TESTS = [
    "test_modeling_camembert.py",
    "test_modeling_tf_camembert.py",
    "test_modeling_tf_xlm_roberta.py",
    "test_modeling_xlm_roberta.py",
]

# Update this list for models that are not documented with a comment explaining the reason it should not be.
# Being in this list is an exception and should **not** be the rule.
IGNORE_NON_DOCUMENTED = [
    "DPREncoder",  # Building part of bigger (documented) model.
    "DPRSpanPredictor",  # Building part of bigger (documented) model.
    "T5Stack",  # Building part of bigger (tested) model.
    "TFElectraMainLayer",  # Building part of bigger (documented) model (should it be a TFPreTrainedModel ?)
]

# Update this dict with any special correspondance model name (used in modeling_xxx.py) to doc file.
MODEL_NAME_TO_DOC_FILE = {
    "openai": "gpt.rst",
    "transfo_xl": "transformerxl.rst",
    "xlm_roberta": "xlmroberta.rst",
}

# This is to make sure the transformers module imported is the one in the repo.
spec = importlib.util.spec_from_file_location(
    "transformers",
    os.path.join(PATH_TO_TRANSFORMERS, "__init__.py"),
    submodule_search_locations=[PATH_TO_TRANSFORMERS],
)
transformers = spec.loader.load_module()


# If some modeling modules should be ignored for all checks, they should be added in the nested list
# _ignore_module of this function.
def get_model_modules():
    """ Get the model modules inside the transformers library. """
    _ignore_module = [
        "modeling_auto",
        "modeling_encoder_decoder",
        "modeling_marian",
        "modeling_mmbt",
        "modeling_outputs",
        "modeling_retribert",
        "modeling_utils",
        "modeling_transfo_xl_utilities",
        "modeling_tf_auto",
        "modeling_tf_outputs",
        "modeling_tf_pytorch_utils",
        "modeling_tf_utils",
        "modeling_tf_transfo_xl_utilities",
    ]
    modules = []
    for attr_name in dir(transformers):
        if attr_name.startswith("modeling") and attr_name not in _ignore_module:
            module = getattr(transformers, attr_name)
            if inspect.ismodule(module):
                modules.append(module)
    return modules


def get_models(module):
    """ Get the objects in module that are models."""
    models = []
    model_classes = (transformers.PreTrainedModel, transformers.TFPreTrainedModel)
    for attr_name in dir(module):
        if "Pretrained" in attr_name or "PreTrained" in attr_name:
            continue
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, model_classes) and attr.__module__ == module.__name__:
            models.append((attr_name, attr))
    return models


# If some test_modeling files should be ignored for the check models are tested, they should be added in the
# nested list _ignore_module of this function.
def get_model_test_files():
    """ Get the model test files."""
    _ignore_files = [
        "test_modeling_common",
        "test_modeling_encoder_decoder",
        "test_modeling_marian",
        "test_modeling_mbart",
        "test_modeling_tf_common",
    ]
    test_files = []
    for filename in os.listdir(PATH_TO_TESTS):
        if (
            os.path.isfile(f"{PATH_TO_TESTS}/{filename}")
            and filename.startswith("test_modeling")
            and not filename[:-3] in _ignore_files
        ):
            test_files.append(filename)
    return test_files


# If some doc files should be ignored for the check models are documented, they should be added in the
# nested list _ignore_module of this function.
def get_model_doc_files():
    """ Get the model doc files."""
    _ignore_files = [
        "auto",
        "dialogpt",
        "marian",
        "retribert",
    ]
    doc_files = []
    for filename in os.listdir(PATH_TO_DOC):
        if os.path.isfile(f"{PATH_TO_DOC}/{filename}") and not filename[:-4] in _ignore_files:
            doc_files.append(filename)
    return doc_files


# This is a bit hacky but I didn't find a way to import the test_file as a module and read inside the tester class
# for the all_model_classes variable.
def find_tested_models(test_file):
    """ Parse the content of test_file to detect what's in all_model_classes"""
    with open(os.path.join(PATH_TO_TESTS, test_file)) as f:
        content = f.read()
    all_models = re.search(r"all_model_classes\s+=\s+\(\s*\(([^\)]*)\)", content)
    # Check with one less parenthesis
    if all_models is None:
        all_models = re.search(r"all_model_classes\s+=\s+\(([^\)]*)\)", content)
    if all_models is not None:
        model_tested = []
        for line in all_models.groups()[0].split(","):
            name = line.strip()
            if len(name) > 0:
                model_tested.append(name)
        return model_tested


def check_models_are_tested(module, test_file):
    """ Check models defined in module are tested in test_file."""
    defined_models = get_models(module)
    tested_models = find_tested_models(test_file)
    if tested_models is None:
        if test_file in TEST_FILES_WITH_NO_COMMON_TESTS:
            return
        return [
            f"{test_file} should define `all_model_classes` to apply common tests to the models it tests. "
            + "If this intentional, add the test filename to `TEST_FILES_WITH_NO_COMMON_TESTS` in the file "
            + "`utils/check_repo.py`."
        ]
    failures = []
    for model_name, _ in defined_models:
        if model_name not in tested_models and model_name not in IGNORE_NON_TESTED:
            failures.append(
                f"{model_name} is defined in {module.__name__} but is not tested in "
                + f"{os.path.join(PATH_TO_TESTS, test_file)}. Add it to the all_model_classes in that file."
                + "If common tests should not applied to that model, add its name to `IGNORE_NON_TESTED`"
                + "in the file `utils/check_repo.py`."
            )
    return failures


def check_all_models_are_tested():
    """ Check all models are properly tested."""
    modules = get_model_modules()
    test_files = get_model_test_files()
    failures = []
    for module in modules:
        test_file = f"test_{module.__name__.split('.')[1]}.py"
        if test_file not in test_files:
            failures.append(f"{module.__name__} does not have its corresponding test file {test_file}.")
        new_failures = check_models_are_tested(module, test_file)
        if new_failures is not None:
            failures += new_failures
    if len(failures) > 0:
        raise Exception(f"There were {len(failures)} failures:\n" + "\n".join(failures))


def find_documented_classes(doc_file):
    """ Parse the content of doc_file to detect which classes it documents"""
    with open(os.path.join(PATH_TO_DOC, doc_file)) as f:
        content = f.read()
    return re.findall(r"autoclass:: transformers.(\S+)\s+", content)


def check_models_are_documented(module, doc_file):
    """ Check models defined in module are documented in doc_file."""
    defined_models = get_models(module)
    documented_classes = find_documented_classes(doc_file)
    failures = []
    for model_name, _ in defined_models:
        if model_name not in documented_classes and model_name not in IGNORE_NON_DOCUMENTED:
            failures.append(
                f"{model_name} is defined in {module.__name__} but is not documented in "
                + f"{os.path.join(PATH_TO_DOC, doc_file)}. Add it to that file."
                + "If this model should not be documented, add its name to `IGNORE_NON_DOCUMENTED`"
                + "in the file `utils/check_repo.py`."
            )
    return failures


def _get_model_name(module):
    """ Get the model name for the module defining it."""
    splits = module.__name__.split("_")
    # Secial case for transfo_xl
    if splits[-1] == "xl":
        return "_".join(splits[-2:])
    # Secial case for xlm_roberta
    if splits[-1] == "roberta" and splits[-2] == "xlm":
        return "_".join(splits[-2:])
    return splits[-1]


def check_all_models_are_documented():
    """ Check all models are properly documented."""
    modules = get_model_modules()
    doc_files = get_model_doc_files()
    failures = []
    for module in modules:
        model_name = _get_model_name(module)
        doc_file = MODEL_NAME_TO_DOC_FILE.get(model_name, f"{model_name}.rst")
        if doc_file not in doc_files:
            failures.append(
                f"{module.__name__} does not have its corresponding doc file {doc_file}. "
                + f"If the doc file exists but isn't named {doc_file}, update `MODEL_NAME_TO_DOC_FILE` "
                + "in the file `utils/check_repo.py`."
            )
        new_failures = check_models_are_documented(module, doc_file)
        if new_failures is not None:
            failures += new_failures
    if len(failures) > 0:
        raise Exception(f"There were {len(failures)} failures:\n" + "\n".join(failures))


def check_repo_quality():
    """ Check all models are properly tested and documented."""
    print("Checking all models are properly tested.")
    check_all_models_are_tested()
    print("Checking all models are properly documented.")
    check_all_models_are_documented()


if __name__ == "__main__":
    check_repo_quality()
