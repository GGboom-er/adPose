#ifdef maya2024
#define python3 1
#endif 
#ifdef maya2022
#define python3 1
#endif // maya2022
#ifdef maya2023
#define python3 1
#endif // maya2022
#ifdef python3
#include <Python37/Python/Python.h>
#else
#include <python2.7/Python.h>
#endif
#include "maya/MPointArray.h"
#include "maya/MVector.h"
#include "maya/MVectorArray.h"
#include "maya/MPoint.h"
#include "maya/MDoubleArray.h"
#include "maya/MIntArray.h"
#include "maya/MStringArray.h"
#include "maya/MString.h"
#define TV(t, i) t v##i;GetPyC<t>(args, i, v##i);

#define FunCToPy0(fun)\
PyObject* fun(PyObject* self, PyObject* args){\
    fun();\
    return Py_None;\
}\

#define FunCToPy1(fun, t0)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)\
    fun(v0);\
    return c_to_py(v0);\
}\


#define FunCToPy2(fun, t0, t1)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)\
    fun(v0,v1);\
    return c_to_py(v1);\
}\


#define FunCToPy3(fun, t0, t1, t2)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)\
    fun(v0,v1,v2);\
    return c_to_py(v2);\
}\


#define FunCToPy4(fun, t0, t1, t2, t3)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)\
    fun(v0,v1,v2,v3);\
    return c_to_py(v3);\
}\


#define FunCToPy5(fun, t0, t1, t2, t3, t4)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)TV(t4, 4)\
    fun(v0,v1,v2,v3,v4);\
    return c_to_py(v4);\
}\


#define FunCToPy6(fun, t0, t1, t2, t3, t4, t5)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)TV(t4, 4)TV(t5, 5)\
    fun(v0,v1,v2,v3,v4,v5);\
    return c_to_py(v5);\
}\


#define FunCToPy7(fun, t0, t1, t2, t3, t4, t5, t6)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)TV(t4, 4)TV(t5, 5)TV(t6, 6)\
    fun(v0,v1,v2,v3,v4,v5,v6);\
    return c_to_py(v6);\
}\


#define FunCToPy8(fun, t0, t1, t2, t3, t4, t5, t6, t7)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)TV(t4, 4)TV(t5, 5)TV(t6, 6)TV(t7, 7)\
    fun(v0,v1,v2,v3,v4,v5,v6,v7);\
    return c_to_py(v7);\
}\


#define FunCToPy9(fun, t0, t1, t2, t3, t4, t5, t6, t7, t8)\
PyObject* fun(PyObject* self, PyObject* args){\
    TV(t0, 0)TV(t1, 1)TV(t2, 2)TV(t3, 3)TV(t4, 4)TV(t5, 5)TV(t6, 6)TV(t7, 7)TV(t8, 8)\
    fun(v0,v1,v2,v3,v4,v5,v6,v7,v8);\
    return c_to_py(v8);\
}\


void py_to_c(PyObject* py_obj, int& c_obj) {
    c_obj = PyLong_AsLong(py_obj);
}

PyObject* c_to_py(int& c_obj) {
    return PyLong_FromLong(c_obj);
}

void py_to_c(PyObject* py_obj, double& c_obj) {
    c_obj = PyFloat_AsDouble(py_obj);
}

PyObject* c_to_py(double& c_obj) {
    return PyFloat_FromDouble(c_obj);
}

void py_to_c(PyObject* py_obj, float& c_obj) {
    c_obj = (float)PyFloat_AsDouble(py_obj);

}

PyObject* c_to_py(float& c_obj) {
    return PyFloat_FromDouble(c_obj);
}

PyObject* c_to_py(MString& c_obj) {
    return PyUnicode_FromString(c_obj.asChar());
}

#ifdef python3
void py_to_c(PyObject* py_obj, MString& c_obj) {
    Py_ssize_t len = PyUnicode_GetLength(py_obj);
    c_obj = PyUnicode_AsWideCharString(py_obj, &len);
}
#else
void py_to_c(PyObject* py_obj, MString& c_obj) {
    c_obj = PyString_AsString(py_obj);
}
#endif


void py_to_c(PyObject* py_obj, MPoint& c_obj) {
    py_to_c(PyList_GetItem(py_obj, 0), c_obj.x);
    py_to_c(PyList_GetItem(py_obj, 1), c_obj.y);
    py_to_c(PyList_GetItem(py_obj, 2), c_obj.z);
}

PyObject* c_to_py(MPoint& c_obj) {
    PyObject* py_obj = PyList_New(3);
    PyList_SetItem(py_obj, 0, c_to_py(c_obj.x));
    PyList_SetItem(py_obj, 1, c_to_py(c_obj.y));
    PyList_SetItem(py_obj, 2, c_to_py(c_obj.z));
    return py_obj;
}

void py_to_c(PyObject* py_obj, MVector& c_obj) {
    py_to_c(PyList_GetItem(py_obj, 0), c_obj.x);
    py_to_c(PyList_GetItem(py_obj, 1), c_obj.y);
    py_to_c(PyList_GetItem(py_obj, 2), c_obj.z);
}

PyObject* c_to_py(MVector& c_obj) {
    PyObject* py_obj = PyList_New(3);
    PyList_SetItem(py_obj, 0, c_to_py(c_obj.x));
    PyList_SetItem(py_obj, 1, c_to_py(c_obj.y));
    PyList_SetItem(py_obj, 2, c_to_py(c_obj.z));
    return py_obj;
}

template <class ArryT, class ElemeT>
void py_list_to_m_arr(PyObject* py_obj, ArryT& c_obj) {
    int length = (int)PyObject_Length(py_obj);
    c_obj.setLength(length);
    for (int i = 0; i < length; i++) {
        ElemeT c_elem;
        PyObject* py_elem = PyList_GetItem(py_obj, i);
        py_to_c(py_elem, c_elem);
        c_obj[i] = c_elem;
    }
}

void py_to_c(PyObject* py_obj, MIntArray& c_obj) {
    py_list_to_m_arr<MIntArray, int>(py_obj, c_obj);
}

void py_to_c(PyObject* py_obj, MDoubleArray& c_obj) {
    py_list_to_m_arr<MDoubleArray, double>(py_obj, c_obj);
}

void py_to_c(PyObject* py_obj, MStringArray& c_obj) {
    py_list_to_m_arr<MStringArray, MString>(py_obj, c_obj);
}

void py_to_c(PyObject* py_obj, MPointArray& c_obj) {
    py_list_to_m_arr<MPointArray, MPoint>(py_obj, c_obj);
}

void py_to_c(PyObject* py_obj, MVectorArray& c_obj) {
    py_list_to_m_arr<MVectorArray, MVector>(py_obj, c_obj);
}

template <class ArryT, class ElemT>
PyObject* m_arr_to_list(ArryT& c_obj) {
    int length = c_obj.length();
    PyObject* py_obj = PyList_New(length);
    for (int i = 0; i < length; i++) {
        ElemT c_elem = c_obj[i];
        PyObject* elem = c_to_py(c_elem);
        PyList_SetItem(py_obj, i, elem);
    }
    return py_obj;
}

PyObject* c_to_py(MIntArray& c_obj) {
    return m_arr_to_list<MIntArray, int>(c_obj);
}

PyObject* c_to_py(MDoubleArray& c_obj) {
    return m_arr_to_list<MDoubleArray, double>(c_obj);
}

PyObject* c_to_py(MStringArray& c_obj) {
    return m_arr_to_list<MStringArray, MString>(c_obj);
}

PyObject* c_to_py(MPointArray& c_obj) {
    return m_arr_to_list<MPointArray, MPoint>(c_obj);
}

PyObject* c_to_py(MVectorArray& c_obj) {
    return m_arr_to_list<MVectorArray, MVector>(c_obj);
}


template<class T>
void GetPyC(PyObject* args, int i, T& c_arg) {
    int length = (int)PyTuple_Size(args);
    if (i >= length) {
        return;
    }
    py_to_c(PyTuple_GetItem(args, i), c_arg);
}

#define PyDef(fun) {#fun, fun, METH_VARARGS, ""}
#define PyDefList(...) static PyMethodDef SpamMethods[] = {__VA_ARGS__,{NULL, NULL, 0, NULL}};

#ifdef python3
#define PyMod(mod) \
static struct PyModuleDef spammodule = {PyModuleDef_HEAD_INIT, #mod, NULL,-1, SpamMethods};\
PyMODINIT_FUNC PyInit_##mod(void) {\
    return PyModule_Create(&spammodule);\
}
#else
#define PyMod(mod) \
PyMODINIT_FUNC init##mod(void) {\
    (void)Py_InitModule(#mod, SpamMethods);\
}
#endif // python3






