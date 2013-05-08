# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# (C) British Crown Copyright 2012-3 Met Office.
# 
# This file is part of Rose, a framework for scientific suites.
# 
# Rose is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Rose is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Rose. If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------


class ConfigDataHelper(object):

    def __init__(self, data, util):
        self.data = data
        self.util = util

    def get_config_meta_flag(self, config):
        """Return the metadata id flag."""
        for keylist in [[rose.CONFIG_SECT_TOP, rose.CONFIG_OPT_META_TYPE],
                        [rose.CONFIG_SECT_TOP, rose.CONFIG_OPT_PROJECT]]:
            type_node = config.get(keylist, no_ignore=True)
            if type_node is not None and type_node.value:
                return type_node.value
        return None

    def get_config_is_discovery(self, config):
        """Return whether a configuration is a discovery configuration."""
        # The logic here will be improved once suite integration is worked on.
        node = config.get([rose.CONFIG_SECT_TOP, rose.CONFIG_OPT_PROJECT])
        return node is not None

    def is_ns_in_tree(self, ns):
        spaces = ns.lstrip('/').split('/')
        subtree = self.data.namespace_tree
        while spaces:
            if spaces[0] not in subtree:
                return False
            subtree = subtree[spaces[0]][0]
            spaces.pop(0)
        return True

    def is_ns_sub_data(self, ns):
        """Return whether a namespace is mentioned in summary data."""
        ns_meta = self.data.namespace_meta_lookup.get(ns, {})
        if (ns_meta.get(rose.META_PROP_DUPLICATE) == rose.META_PROP_VALUE_TRUE
            and not ns.split("/")[-1].isdigit() and
            len([n for n in self.data.namespace_meta_lookup
                 if n.startswith(ns)]) > 1):
            return True
        if ns.split("/")[-1] == rose.SUB_CONFIG_FILE_DIR:
            return True
        return False

    def is_ns_content(self, ns):
        """Return whether a namespace has any existing content."""
        config_name = self.util.split_full_ns(self, ns)[0]
        for section in self.data.get_sections_from_namespace(ns):
            if section in self.data.config[config_name].sections.now:
                return True
        return self.is_ns_sub_data(ns)

    def get_metadata_for_config_id(self, node_id, config_name):
        """Retrieve the corresponding metadata for a variable."""
        config_data = self.data.config[config_name]
        meta_config = config_data.meta
        meta_data = {}
        if not node_id:
            return {'id': node_id}
        return rose.macro.get_metadata_for_config_id(node_id, meta_config)

    def get_variable_by_id(self, var_id, config_name, save=False,
                           latent=False):
        """Return the matching variable or None."""
        sect, opt = self.util.get_section_option_from_id(var_id)
        return self.data.config[config_name].vars.get_var(
                         sect, opt, save, no_latent=not latent)

#------------------ Data model helper functions ------------------------------

    def get_data_for_namespace(self, ns, from_saved=False):
        """Return a list of vars and a list of latent vars for this ns."""
        config_name = self.util.split_full_ns(self, ns)[0]
        config_data = self.data.config[config_name]
        allowed_sections = self.get_sections_from_namespace(ns)
        variables = []
        latents = []
        if from_saved:
            var_map = config_data.vars.save
            latent_var_map = config_data.vars.latent_save
        else:
            var_map = config_data.vars.now
            latent_var_map = config_data.vars.latent
        for section in allowed_sections:
            variables.extend(var_map.get(section, []))
            latents.extend(latent_var_map.get(section, []))
        ns_vars = [v for v in variables if v.metadata.get('full_ns') == ns]
        ns_latents = [v for v in latents if v.metadata.get('full_ns') == ns]
        return ns_vars, ns_latents

    def get_sub_data_for_namespace(self, ns, from_saved=False):
        """Return any sections/variables below this namespace."""
        sub_data = {"sections": {}, "variables": {}}
        config_name = self.util.split_full_ns(self, ns)[0]
        config_data = self.data.config[config_name]
        for sect, sect_data in config_data.sections.now.items():
            sect_ns = sect_data.metadata["full_ns"]
            if sect_ns.startswith(ns):
                sub_data["sections"].update({sect: sect_data})
        sub_data["get_var_id_values_func"] = (
                lambda: self.get_sub_data_var_id_values(config_name))
        for sect, variables in config_data.vars.now.items():
            for variable in variables:
                if variable.metadata["full_ns"].startswith(ns):
                    sub_data["variables"].setdefault(sect, [])
                    sub_data["variables"][sect].append(variable)
        if not sub_data["sections"] and not sub_data["variables"]:
            return None
        return sub_data

    def get_sub_data_var_id_value_map(self, config_name):
        """Return all real (=existing) variable values for sub data."""
        config_data = self.data.config[config_name]
        var_id_val_map = {}
        for variable in config_data.vars.get_all():
            var_id_val_map.update({variable.metadata["id"]: variable.value})
        return var_id_val_map

    def get_ns_comment_string(self, ns):
        """Return a comment string for this namespace."""
        comment = ""
        comments = []
        config_name = self.util.split_full_ns(self, ns)[0]
        config_data = self.data.config[config_name]
        sections = self.get_sections_from_namespace(ns)
        sections.sort(rose.config.sort_settings)
        for section in sections:
            sect_data = config_data.sections.now.get(section)
            if sect_data is not None and sect_data.comments:
                comments.extend(sect_data.comments)
        if comments:
            comment = "#" + "\n#".join(comments)
        return comment

    def get_ns_variable(self, var_id, ns):
        """Return a variable with this id in the config specified by ns."""
        config_name = self.util.split_full_ns(self, ns)[0]
        config_data = self.data.config[config_name]
        sect, opt = self.util.get_section_option_from_id(var_id)
        var = config_data.vars.get_var(sect, opt)
        if var is None:
            var = config_data.vars.get_var(sect, opt, save=True)
        return var  # May be None.
            
    def get_sections_from_namespace(self, namespace):
        """Return all sections contributing to a namespace."""
        # FIXME: What about files?
        ns_metadata = self.data.namespace_meta_lookup.get(namespace, {})
        sections = ns_metadata.get('sections', [])
        if sections:
            return [s for s in sections]
        base, subsp = self.util.split_full_ns(self, namespace)
        ns_section = subsp.replace('/', ':')
        if (ns_section in self.data.config[base].sections.now or
            ns_section in self.data.config[base].sections.latent):
            return [ns_section]
        return []

    def get_all_namespaces(self, only_this_config=None):
        """Return all unique namespaces."""
        all_namespaces = []
        if only_this_config is None:
            configs = self.data.config.keys()
        else:
            configs = [only_this_config]
        for config_name in configs:
            all_namespaces += [config_name]
            self.data.load_node_namespaces(config_name)
            for var in self.data.config[config_name].vars.get_all():
                all_namespaces.append(var.metadata["full_ns"])
            for sect_data in self.data.config[config_name].sections.now.values():
                all_namespaces.append(sect_data.metadata["full_ns"])
        unique_namespaces = []
        for ns in all_namespaces:
            if ns not in unique_namespaces:
                unique_namespaces.append(ns)
        unique_namespaces.sort(lambda x, y: y.count('/') - x.count('/'))
        return unique_namespaces

    def get_missing_sections(self, config_name=None):
        """Return full section ids that are missing."""
        full_sections = []
        if config_name is not None:
            config_names = [config_name]
        else:
            config_names = self.data.config.keys()
        for config_name in config_names:
            section_store = self.data.config[config_name].sections
            miss_sections = []
            real_sections = section_store.now.keys()
            for section in section_store.latent.keys():
                if section not in real_sections:
                    miss_sections.append(section)
            for section in self.data.config[config_name].vars.latent:
                if (section not in real_sections and
                    section not in miss_sections):
                    miss_sections.append(section)
            full_sections += [config_name + ':' + s for s in miss_sections]
        sorter = rose.config.sort_settings
        full_sections.sort(sorter)
        return full_sections

    def get_default_namespace_for_section(self, section, config_name):
        """Return the default namespace for the section."""
        if config_name not in self.data._config_section_namespace_lookup:
            self.data._config_section_namespace_lookup.setdefault(
                                                config_name, {})
        section_ns = self._config_section_namespace_lookup[config_name].get(
                                                                  section)
        if section_ns is None:
            config_data = self.data.config[config_name]
            meta_config = config_data.meta
            node = meta_config.get([section, rose.META_PROP_NS], no_ignore=True)
            if node is not None:
                subspace = node.value
            else:
                match = REC_ELEMENT_SECTION.match(section)
                if match:
                    node = meta_config.get([match.groups()[0], rose.META_PROP_NS])
                    if node is None or node.is_ignored():
                        subspace = section.replace('(', '/')
                        subspace = subspace.replace(')', '')
                        subspace = subspace.replace(':', '/')
                    else:
                        subspace = node.value + '/' + str(match.groups()[1])
                elif section.startswith(rose.SUB_CONFIG_FILE_DIR + ":"):
                    subspace = section.replace('/', ':')
                    subspace = subspace.replace(':', '/', 1)
                else:
                    subspace = section.replace(':', '/')
            section_ns = config_name + '/' + subspace
            if not subspace:
                section_ns = config_name
            self._config_section_namespace_lookup[config_name].update(
                                           {section: section_ns})
        return section_ns

    def get_format_sections(self, config_name):
        """Return all format-like sections in the current data."""
        format_keys = []
        for section in self.data.config[config_name].sections.now:
            if (section not in format_keys and 
                ':' in section and not section.startswith('file:')):
                format_keys.append(section)
        format_keys.sort(rose.config.sort_settings)
        return format_keys

    def get_icon_path_for_config(self, config_name):
        """Return the path to the config identifier icon or None."""
        icon_path = None
        for filename in self.data.config[config_name].meta_files:
            if filename.endswith('/images/icon.png'):
                icon_path = filename
                break
        return icon_path

    def get_ns_ignored_status(self, namespace):
        """Return the ignored status for a namespace's data."""
        config_name = self.util.split_full_ns(self, namespace)[0]
        config_data = self.data.config[config_name]
        sections = self.get_sections_from_namespace(namespace)
        status = rose.config.ConfigNode.STATE_NORMAL
        object_statuses = {}
        for section in sections:
            sect_data = config_data.sections.get_sect(section)
            if sect_data.metadata["full_ns"] == namespace:
                if not sect_data.ignored_reason:
                    return status
        real_data, latent_data = self.get_data_for_namespace(namespace)
        for var in real_data + latent_data:
            if not var.ignored_reason:
                return status
            for key in var.ignored_reason:
                if key == rose.variable.IGNORED_BY_SECTION:
                    # Section ignored statuses need interpreting.
                    var_id = var.metadata["id"]
                    section, option = self.util.get_section_option_from_id(
                                                                   var_id)
                    sect_data = config_data.sections.get_sect(section)
                    for key in sect_data.ignored_reason:
                        object_statuses.setdefault(key, 0)
                        object_statuses[key] += 1
                else:
                    object_statuses.setdefault(key, 0)
                    object_statuses[key] += 1
        if not object_statuses:
            # No data, so no ignored state.
            return status
        # Now return the most 'popular' ignored status.
        status_counts = object_statuses.items()
        status_counts.sort(lambda x, y: cmp(x[1], y[1]))
        status = status_counts[0][0]
        if status == rose.variable.IGNORED_BY_USER:
            return rose.config.ConfigNode.STATE_USER_IGNORED
        if status == rose.variable.IGNORED_BY_SYSTEM:
            return rose.config.ConfigNode.STATE_SYST_IGNORED
        return rose.config.ConfigNode.STATE_NORMAL
