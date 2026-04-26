/*
 * Заготовка DLL для МКБ-С-3.
 * Экспортирует только версию библиотеки и может быть расширена
 * функциями поиска/фильтрации кодов в нативном модуле.
 */

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT
#endif

DLL_EXPORT const char* get_mkb_s3_version(void) {
    return "mkb_s3_dll_stub_1.0";
}
