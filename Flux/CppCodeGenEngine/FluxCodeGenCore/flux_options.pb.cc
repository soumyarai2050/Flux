// Generated by the protocol buffer compiler.  DO NOT EDIT!

#define INTERNAL_SUPPRESS_PROTOBUF_FIELD_DEPRECATION
#include "flux_options.pb.h"

#include <algorithm>

#include <google/protobuf/stubs/once.h>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/wire_format_lite_inl.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/reflection_ops.h>
#include <google/protobuf/wire_format.h>
// @@protoc_insertion_point(includes)

namespace {


}  // namespace


void protobuf_AssignDesc_flux_5foptions_2eproto() {
  protobuf_AddDesc_flux_5foptions_2eproto();
  const ::google::protobuf::FileDescriptor* file =
    ::google::protobuf::DescriptorPool::generated_pool()->FindFileByName(
      "flux_options.proto");
  GOOGLE_CHECK(file != NULL);
}

namespace {

GOOGLE_PROTOBUF_DECLARE_ONCE(protobuf_AssignDescriptors_once_);
inline void protobuf_AssignDescriptorsOnce() {
  ::google::protobuf::GoogleOnceInit(&protobuf_AssignDescriptors_once_,
                 &protobuf_AssignDesc_flux_5foptions_2eproto);
}

void protobuf_RegisterTypes(const ::std::string&) {
  protobuf_AssignDescriptorsOnce();
}

}  // namespace

void protobuf_ShutdownFile_flux_5foptions_2eproto() {
}

void protobuf_AddDesc_flux_5foptions_2eproto() {
  static bool already_here = false;
  if (already_here) return;
  already_here = true;
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  ::google::protobuf::protobuf_AddDesc_google_2fprotobuf_2fdescriptor_2eproto();
  ::google::protobuf::DescriptorPool::InternalAddGeneratedFile(
    "\n\022flux_options.proto\032 google/protobuf/de"
    "scriptor.proto:4\n\014FluxFileCmnt\022\034.google."
    "protobuf.FileOptions\030\317\217\003 \001(\t:9\n\021FluxFile"
    "ModelType\022\034.google.protobuf.FileOptions\030"
    "\320\217\003 \001(\t:6\n\013FluxMsgCmnt\022\037.google.protobuf"
    ".MessageOptions\030\317\217\003 \001(\t:8\n\rFluxMsgRootId"
    "\022\037.google.protobuf.MessageOptions\030\320\217\003 \001("
    "\t:\?\n\024FluxMsgPrefixPrepend\022\037.google.proto"
    "buf.MessageOptions\030\321\217\003 \001(\t:5\n\nFluxMsgTbl"
    "\022\037.google.protobuf.MessageOptions\030\267\227\003 \001("
    "\t:;\n\020FluxMsgTblShared\022\037.google.protobuf."
    "MessageOptions\030\270\227\003 \001(\t:8\n\rFluxMsgOpName\022"
    "\037.google.protobuf.MessageOptions\030\237\237\003 \001(\t"
    ":5\n\nFluxMsgRsp\022\037.google.protobuf.Message"
    "Options\030\240\237\003 \001(\t:8\n\rFluxMsgNotify\022\037.googl"
    "e.protobuf.MessageOptions\030\241\237\003 \001(\t:\?\n\024Flu"
    "xMsgDaoAccessType\022\037.google.protobuf.Mess"
    "ageOptions\030\207\247\003 \001(\t::\n\017FluxMsgNoExpand\022\037."
    "google.protobuf.MessageOptions\030\210\247\003 \001(\t:9"
    "\n\016FluxMsgOrmRoot\022\037.google.protobuf.Messa"
    "geOptions\030\357\256\003 \001(\t:P\n%FluxMsgOrmCreateUpd"
    "ateOrDeleteClasses\022\037.google.protobuf.Mes"
    "sageOptions\030\360\256\003 \001(\t:D\n\031FluxMsgOrmReadRes"
    "pClasses\022\037.google.protobuf.MessageOption"
    "s\030\361\256\003 \001(\t:;\n\020FluxMsgCmplxHigh\022\037.google.p"
    "rotobuf.MessageOptions\030\327\266\003 \001(\t::\n\017FluxMs"
    "gCmplxMed\022\037.google.protobuf.MessageOptio"
    "ns\030\330\266\003 \001(\t::\n\017FluxMsgCmplxLow\022\037.google.p"
    "rotobuf.MessageOptions\030\331\266\003 \001(\t:4\n\013FluxFl"
    "dCmnt\022\035.google.protobuf.FieldOptions\030\317\217\003"
    " \001(\t:4\n\013FluxFldHide\022\035.google.protobuf.Fi"
    "eldOptions\030\320\217\003 \001(\t:4\n\013FluxFldHelp\022\035.goog"
    "le.protobuf.FieldOptions\030\321\217\003 \001(\t:3\n\nFlux"
    "FldTbl\022\035.google.protobuf.FieldOptions\030\267\227"
    "\003 \001(\t:3\n\nFluxFldCol\022\035.google.protobuf.Fi"
    "eldOptions\030\270\227\003 \001(\t:2\n\tFluxFldPk\022\035.google"
    ".protobuf.FieldOptions\030\271\227\003 \001(\t:5\n\014FluxFl"
    "dFkTbl\022\035.google.protobuf.FieldOptions\030\272\227"
    "\003 \001(\t:5\n\014FluxFldFkCol\022\035.google.protobuf."
    "FieldOptions\030\273\227\003 \001(\t:9\n\020FluxFldCmplxHigh"
    "\022\035.google.protobuf.FieldOptions\030\327\266\003 \001(\t:"
    "8\n\017FluxFldCmplxMed\022\035.google.protobuf.Fie"
    "ldOptions\030\330\266\003 \001(\t:8\n\017FluxFldCmplxLow\022\035.g"
    "oogle.protobuf.FieldOptions\030\331\266\003 \001(\t:6\n\rF"
    "luxFldValMin\022\035.google.protobuf.FieldOpti"
    "ons\030\217\316\003 \001(\t:6\n\rFluxFldValMax\022\035.google.pr"
    "otobuf.FieldOptions\030\220\316\003 \001(\t:7\n\016FluxFldVa"
    "lList\022\035.google.protobuf.FieldOptions\030\221\316\003"
    " \001(\t:7\n\016FluxFldTestVal\022\035.google.protobuf"
    ".FieldOptions\030\222\316\003 \001(\t:;\n\022FluxFldValDateT"
    "ime\022\035.google.protobuf.FieldOptions\030\223\316\003 \001"
    "(\t:>\n\025FluxFldMappingSrcType\022\035.google.pro"
    "tobuf.FieldOptions\030\367\325\003 \001(\t", 2106);
  ::google::protobuf::MessageFactory::InternalRegisterGeneratedFile(
    "flux_options.proto", &protobuf_RegisterTypes);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FileOptions::default_instance(),
    51151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FileOptions::default_instance(),
    51152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    51151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    51152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    51153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    52151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    52152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    53151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    53152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    53153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    54151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    54152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    55151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    55152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    55153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    56151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    56152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::MessageOptions::default_instance(),
    56153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    51151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    51152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    51153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    52151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    52152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    52153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    52154, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    52155, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    56151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    56152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    56153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    59151, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    59152, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    59153, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    59154, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    59155, 9, false, false);
  ::google::protobuf::internal::ExtensionSet::RegisterExtension(
    &::google::protobuf::FieldOptions::default_instance(),
    60151, 9, false, false);
  ::google::protobuf::internal::OnShutdown(&protobuf_ShutdownFile_flux_5foptions_2eproto);
}

// Force AddDescriptors() to be called at static initialization time.
struct StaticDescriptorInitializer_flux_5foptions_2eproto {
  StaticDescriptorInitializer_flux_5foptions_2eproto() {
    protobuf_AddDesc_flux_5foptions_2eproto();
  }
} static_descriptor_initializer_flux_5foptions_2eproto_;

const ::std::string FluxFileCmnt_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FileOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFileCmnt(kFluxFileCmntFieldNumber, FluxFileCmnt_default);
const ::std::string FluxFileModelType_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FileOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFileModelType(kFluxFileModelTypeFieldNumber, FluxFileModelType_default);
const ::std::string FluxMsgCmnt_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgCmnt(kFluxMsgCmntFieldNumber, FluxMsgCmnt_default);
const ::std::string FluxMsgRootId_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgRootId(kFluxMsgRootIdFieldNumber, FluxMsgRootId_default);
const ::std::string FluxMsgPrefixPrepend_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgPrefixPrepend(kFluxMsgPrefixPrependFieldNumber, FluxMsgPrefixPrepend_default);
const ::std::string FluxMsgTbl_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgTbl(kFluxMsgTblFieldNumber, FluxMsgTbl_default);
const ::std::string FluxMsgTblShared_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgTblShared(kFluxMsgTblSharedFieldNumber, FluxMsgTblShared_default);
const ::std::string FluxMsgOpName_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgOpName(kFluxMsgOpNameFieldNumber, FluxMsgOpName_default);
const ::std::string FluxMsgRsp_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgRsp(kFluxMsgRspFieldNumber, FluxMsgRsp_default);
const ::std::string FluxMsgNotify_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgNotify(kFluxMsgNotifyFieldNumber, FluxMsgNotify_default);
const ::std::string FluxMsgDaoAccessType_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgDaoAccessType(kFluxMsgDaoAccessTypeFieldNumber, FluxMsgDaoAccessType_default);
const ::std::string FluxMsgNoExpand_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgNoExpand(kFluxMsgNoExpandFieldNumber, FluxMsgNoExpand_default);
const ::std::string FluxMsgOrmRoot_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgOrmRoot(kFluxMsgOrmRootFieldNumber, FluxMsgOrmRoot_default);
const ::std::string FluxMsgOrmCreateUpdateOrDeleteClasses_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgOrmCreateUpdateOrDeleteClasses(kFluxMsgOrmCreateUpdateOrDeleteClassesFieldNumber, FluxMsgOrmCreateUpdateOrDeleteClasses_default);
const ::std::string FluxMsgOrmReadRespClasses_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgOrmReadRespClasses(kFluxMsgOrmReadRespClassesFieldNumber, FluxMsgOrmReadRespClasses_default);
const ::std::string FluxMsgCmplxHigh_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgCmplxHigh(kFluxMsgCmplxHighFieldNumber, FluxMsgCmplxHigh_default);
const ::std::string FluxMsgCmplxMed_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgCmplxMed(kFluxMsgCmplxMedFieldNumber, FluxMsgCmplxMed_default);
const ::std::string FluxMsgCmplxLow_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::MessageOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxMsgCmplxLow(kFluxMsgCmplxLowFieldNumber, FluxMsgCmplxLow_default);
const ::std::string FluxFldCmnt_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldCmnt(kFluxFldCmntFieldNumber, FluxFldCmnt_default);
const ::std::string FluxFldHide_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldHide(kFluxFldHideFieldNumber, FluxFldHide_default);
const ::std::string FluxFldHelp_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldHelp(kFluxFldHelpFieldNumber, FluxFldHelp_default);
const ::std::string FluxFldTbl_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldTbl(kFluxFldTblFieldNumber, FluxFldTbl_default);
const ::std::string FluxFldCol_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldCol(kFluxFldColFieldNumber, FluxFldCol_default);
const ::std::string FluxFldPk_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldPk(kFluxFldPkFieldNumber, FluxFldPk_default);
const ::std::string FluxFldFkTbl_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldFkTbl(kFluxFldFkTblFieldNumber, FluxFldFkTbl_default);
const ::std::string FluxFldFkCol_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldFkCol(kFluxFldFkColFieldNumber, FluxFldFkCol_default);
const ::std::string FluxFldCmplxHigh_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldCmplxHigh(kFluxFldCmplxHighFieldNumber, FluxFldCmplxHigh_default);
const ::std::string FluxFldCmplxMed_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldCmplxMed(kFluxFldCmplxMedFieldNumber, FluxFldCmplxMed_default);
const ::std::string FluxFldCmplxLow_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldCmplxLow(kFluxFldCmplxLowFieldNumber, FluxFldCmplxLow_default);
const ::std::string FluxFldValMin_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldValMin(kFluxFldValMinFieldNumber, FluxFldValMin_default);
const ::std::string FluxFldValMax_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldValMax(kFluxFldValMaxFieldNumber, FluxFldValMax_default);
const ::std::string FluxFldValList_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldValList(kFluxFldValListFieldNumber, FluxFldValList_default);
const ::std::string FluxFldTestVal_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldTestVal(kFluxFldTestValFieldNumber, FluxFldTestVal_default);
const ::std::string FluxFldValDateTime_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldValDateTime(kFluxFldValDateTimeFieldNumber, FluxFldValDateTime_default);
const ::std::string FluxFldMappingSrcType_default("");
::google::protobuf::internal::ExtensionIdentifier< ::google::protobuf::FieldOptions,
    ::google::protobuf::internal::StringTypeTraits, 9, false >
  FluxFldMappingSrcType(kFluxFldMappingSrcTypeFieldNumber, FluxFldMappingSrcType_default);

// @@protoc_insertion_point(namespace_scope)

// @@protoc_insertion_point(global_scope)
