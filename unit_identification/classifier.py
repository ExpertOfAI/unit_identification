import json
import logging
import multiprocessing
import os
import warnings
import pkg_resources
from . import language, load
from .load import cached
try:
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    USE_CLF = True
except ImportError:
    SGDClassifier, TfidfVectorizer = None, None
    USE_CLF = False
    warnings.warn(
        "Classifier dependencies not installed. "
        "to install them. The classifier helps to disambiguate units."
    )
try:
    import wikipedia
except ImportError:
    wikipedia = None
_LOGGER = logging.getLogger(__name__)
@cached
def _get_classifier(lang="en_US"):
    return language.get("classifier", lang)
def ambiguous_units(lang="en_US"):
    ambiguous = [
        i for i in list(load.units(lang).surfaces_all.items()) if len(i[1]) > 1
    ]
    ambiguous += [i for i in list(load.units(lang).symbols.items()) if len(i[1]) > 1]
    ambiguous += [i for i in list(load.entities(lang).derived.items()) if len(i[1]) > 1]
    return ambiguous
def download_wiki(store=True, lang="en_US"):
    if not wikipedia:
        print("Cannot download Wikipedia pages. Install package Wikipedia first.")
        return
    wikipedia.set_lang(lang[:2])
    ambiguous = ambiguous_units()
    pages = set([(j.name, j.uri) for i in ambiguous for j in i[1]])
    print()
    objs = []
    for num, page in enumerate(pages):
        obj = {
            "_id": page[1],
            "url": "https://{}.wikipedia.org/wiki/{}".format(lang[:2], page[1]),
            "clean": page[1].replace("_", " "),
        }
        print("---> Downloading %s (%d of %d)" % (obj["clean"], num + 1, len(pages)))
        obj["text"] = wikipedia.page(obj["clean"], auto_suggest=False).content
        obj["unit"] = page[0]
        objs.append(obj)
    path = language.topdir(lang).joinpath("train/wiki.json")
    if store:
        with path.open("w") as wiki_file:
            json.dump(objs, wiki_file, indent=4, sort_keys=True)
    print("\n---> All done.\n")
    return objs
def clean_text(text, lang="en_US"):
    return _get_classifier(lang).clean_text(text)
def _clean_text_lang(lang):
    return _get_classifier(lang).clean_text
def train_classifier(
    parameters=None,
    ngram_range=(1, 1),
    store=True,
    lang="en_US",
    n_jobs=None,
    training_set=None,
    output_path=None,
):
    _LOGGER.info("Started training, parallelized with {} jobs".format(n_jobs))
    _LOGGER.info("Loading training set")
    if training_set is None:
        training_set = load.training_set(lang)
    target_names = list(frozenset([i["unit"] for i in training_set]))
    _LOGGER.info("Preparing training set")
    if n_jobs is None:
        try:
            n_jobs = len(os.sched_getaffinity(0))
        except AttributeError:
            pass
    with multiprocessing.Pool(processes=n_jobs) as p:
        train_data = p.map(_clean_text_lang(lang), [ex["text"] for ex in training_set])
    train_target = [target_names.index(example["unit"]) for example in training_set]
    tfidf_model = TfidfVectorizer(
        sublinear_tf=True,
        ngram_range=ngram_range,
        stop_words=_get_classifier(lang).stop_words(),
    )
    _LOGGER.info("Fit TFIDF Model")
    matrix = tfidf_model.fit_transform(train_data)
    if parameters is None:
        parameters = {
            "loss": "log_loss",
            "penalty": "l2",
            "tol": 1e-3,
            "n_jobs": n_jobs,
            "alpha": 0.0001,
            "fit_intercept": True,
            "random_state": 0,
        }
    _LOGGER.info("Fit SGD Classifier")
    clf = SGDClassifier(**parameters).fit(matrix, train_target)
    obj = {
        "scikit-learn_version": pkg_resources.get_distribution("scikit-learn").version,
        "tfidf_model": tfidf_model,
        "clf": clf,
        "target_names": target_names,
    }
    if store:
        if output_path is not None:
            path = output_path
        else:
            path = language.topdir(lang).joinpath("clf.joblib")
        _LOGGER.info("Store classifier at {}".format(path))
        with open(path, "wb") as file:
            joblib.dump(obj, file)
    return obj
class Classifier(object):
    def __init__(self, classifier_object=None, lang="en_US", classifier_path=None):
        self.tfidf_model = None
        self.classifier = None
        self.target_names = None
        if not USE_CLF:
            return
        if not classifier_object:
            if classifier_path is None:
                classifier_path = language.topdir(lang).joinpath("clf.joblib")
            with open(classifier_path, "rb") as file:
                classifier_object = joblib.load(file)
        cur_scipy_version = pkg_resources.get_distribution("scikit-learn").version
        if cur_scipy_version != classifier_object.get(
            "scikit-learn_version"
        ):
            _LOGGER.warning(
                "The classifier was built using a different scikit-learn "
                "version (={}, !={}). The disambiguation tool could behave "
                "unexpectedly. Consider running classifier.train_classfier()".format(
                    classifier_object.get("scikit-learn_version"), cur_scipy_version
                )
            )
        self.tfidf_model = classifier_object["tfidf_model"]
        self.classifier = classifier_object["clf"]
        self.target_names = classifier_object["target_names"]
@cached
def classifier(lang: str = "en_US", classifier_path: str = None) -> Classifier:
    return Classifier(lang=lang, classifier_path=classifier_path)
def disambiguate_entity(key, text, lang="en_US", classifier_path=None):
    entities_ = load.entities(lang)
    new_ent = next(iter(entities_.derived[key]))
    if len(entities_.derived[key]) > 1:
        classifier_: Classifier = classifier(lang, classifier_path)
        transformed = classifier_.tfidf_model.transform([clean_text(text, lang)])
        scores = classifier_.classifier.predict_proba(transformed).tolist()[0]
        scores = zip(scores, classifier_.target_names)
        names = [i.name for i in entities_.derived[key]]
        scores = [i for i in scores if i[1] in names]
        scores = sorted(scores, key=lambda x: x[0], reverse=True)
        try:
            new_ent = entities_.names[scores[0][1]]
        except IndexError:
            _LOGGER.debug('\tAmbiguity not resolved for "%s"', str(key))
    return new_ent
def disambiguate_unit(unit, text, lang="en_US", classifier_path=None):
    units_ = load.units(lang)
    new_unit = (
        units_.symbols.get(unit)
        or units_.surfaces.get(unit)
        or units_.surfaces_lower.get(unit.lower())
        or units_.symbols_lower.get(unit.lower())
    )
    if not new_unit:
        return units_.names.get("unk")
    if len(new_unit) > 1:
        classifier_: Classifier = classifier(lang, classifier_path)
        transformed = classifier_.tfidf_model.transform([clean_text(text, lang)])
        scores = classifier_.classifier.predict_proba(transformed).tolist()[0]
        scores = zip(scores, classifier_.target_names)
        names = [i.name for i in new_unit]
        scores = [i for i in scores if i[1] in names]
        scores = sorted(scores, key=lambda x: x[0], reverse=True)
        try:
            final = units_.names[scores[0][1]]
            _LOGGER.debug('\tAmbiguity resolved for "%s" (%s)' % (unit, scores))
        except IndexError:
            _LOGGER.debug('\tAmbiguity not resolved for "%s"' % unit)
            final = next(iter(new_unit))
    else:
        final = next(iter(new_unit))
    return final