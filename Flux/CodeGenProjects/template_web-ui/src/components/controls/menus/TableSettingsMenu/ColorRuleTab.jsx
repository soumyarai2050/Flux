import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import Help from '@mui/icons-material/Help';
import Popover from '@mui/material/Popover';
import { isValidColorRule } from '../../../../utils/ui/colorUtils';

/**
 * ColorRuleTab - A separate component for managing color rules with autocomplete field selection
 *
 * Features:
 * - Autocomplete field selector for all columns
 * - Edit/apply color rules for selected field
 * - View active rules (both overrides and schema rules)
 * - Delete rules functionality
 */
const ColorRuleTab = ({
  columns = [],
  colorRules = [],
  onColorRuleOverrideChange,
}) => {
  const [selectedFieldName, setSelectedFieldName] = useState('');
  const [colorRuleInput, setColorRuleInput] = useState('');
  const [backgroundColorRuleInput, setBackgroundColorRuleInput] = useState('');
  const [colorRuleHelpAnchorEl, setColorRuleHelpAnchorEl] = useState(null);

  // Create list of available fields for autocomplete
  const availableFields = useMemo(() => {
    return columns
      .filter((column) => column.sourceIndex === 0)
      .map((column) => ({
        key: column.identifier || column.key,
        label: column.elaborateTitle ? column.identifier : column.key,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [columns]);

  const handleColorRuleFieldSelect = (fieldName) => {
    const existingRule = colorRules.find((rule) => rule.field_name === fieldName);
    setSelectedFieldName(fieldName);
    if (existingRule) {
      setColorRuleInput(existingRule.color_rule || '');
      setBackgroundColorRuleInput(existingRule.background_color_rule || '');
    } else {
      setColorRuleInput('');
      setBackgroundColorRuleInput('');
    }
  };

  const handleApplyColorRule = () => {
    if (!selectedFieldName) return;

    const updatedColorRules = colorRules.filter((rule) => rule.field_name !== selectedFieldName);

    // Only add if at least one rule is non-empty and valid
    const colorRuleValid = colorRuleInput.trim() === '' || isValidColorRule(colorRuleInput);
    const backgroundColorRuleValid = backgroundColorRuleInput.trim() === '' || isValidColorRule(backgroundColorRuleInput);

    if ((colorRuleInput.trim() !== '' || backgroundColorRuleInput.trim() !== '') &&
        colorRuleValid && backgroundColorRuleValid) {
      const newRule = {
        field_name: selectedFieldName,
        color_rule: colorRuleInput.trim() || null,
        background_color_rule: backgroundColorRuleInput.trim() || null,
      };
      updatedColorRules.push(newRule);
    }

    if (onColorRuleOverrideChange) {
      onColorRuleOverrideChange(updatedColorRules);
    }

    setColorRuleInput('');
    setBackgroundColorRuleInput('');
    setSelectedFieldName('');
  };

  const handleDeleteColorRule = (fieldName) => {
    const updatedColorRules = colorRules.filter((rule) => rule.field_name !== fieldName);
    if (onColorRuleOverrideChange) {
      onColorRuleOverrideChange(updatedColorRules);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key.length === 1 || ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  };

  // Helper function to detect if string has conditional operator
  const hasConditionalOperator = (str) => {
    return /[><=]/.test(str);
  };

  // Helper function to intelligently parse different rule formats
  const parseRuleString = (ruleString) => {
    if (!ruleString) return null;

    const parts = ruleString.split('|');

    // Case 1: min|max|rule (3+ pipes) - Complex rule with min/max
    if (parts.length >= 3) {
      return {
        type: 'minMaxRule',
        min: parts[0],
        max: parts[1],
        rule: parts[2],
      };
    }

    // Case 2: direct rule (no pipes, has conditional operator) - e.g., "50>blue"
    if (parts.length === 1 && hasConditionalOperator(parts[0])) {
      return {
        type: 'directRule',
        rule: parts[0],
      };
    }

    // Case 3: src|rule (2 pipes, first part has no conditional operator)
    if (parts.length === 2 && !hasConditionalOperator(parts[0])) {
      return {
        type: 'srcRule',
        src: parts[0],
        rule: parts[1],
      };
    }

    // Case 4: src only (no pipes, no conditional operator) - e.g., "fx_symbol_overview.limit_dn_px"
    if (parts.length === 1 && !hasConditionalOperator(parts[0])) {
      return {
        type: 'srcOnly',
        src: parts[0],
      };
    }

    return null;
  };

  // Helper to extract field name from xpath (last part after .)
  const extractFieldName = (xpath) => {
    if (!xpath) return xpath;
    const parts = xpath.split('.');
    return parts[parts.length - 1];
  };

  // Smart component to render rule, src, or percentage in tabular format
  const SmartRuleDisplay = ({ value, label = 'Rule' }) => {
    if (!value) return null;

    const parsed = parseRuleString(value);

    // Helper to render a table row
    const renderRow = (rowLabel, rowValue, isLast = false) => (
      <div
        style={{
          display: 'table-row',
          borderBottom: isLast ? 'none' : '1px solid rgba(255,255,255,0.15)',
        }}
      >
        <div
          style={{
            display: 'table-cell',
            padding: '5px 8px',
            fontWeight: '600',
            color: 'rgba(255,255,255,0.8)',
            backgroundColor: 'rgba(0,0,0,0.2)',
            width: '50px',
            borderRight: '1px solid rgba(255,255,255,0.15)',
            verticalAlign: 'top',
          }}
        >
          {rowLabel}
        </div>
        <div
          style={{
            display: 'table-cell',
            padding: '5px 8px',
            color: 'white',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
          }}
        >
          {rowValue}
        </div>
      </div>
    );

    if (!parsed) {
      // Fallback for unparseable values
      return <span style={{ fontSize: '10px', color: 'white' }}>{value}</span>;
    }

    // Case 1: min|max|rule format
    if (parsed.type === 'minMaxRule') {
      const minFieldName = extractFieldName(parsed.min);
      const maxFieldName = extractFieldName(parsed.max);

      return (
        <div
          style={{
            display: 'table',
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '9px',
            backgroundColor: 'rgba(0,0,0,0.15)',
            borderRadius: '3px',
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          {renderRow('Min', minFieldName)}
          {renderRow('Max', maxFieldName)}
          {renderRow(label, parsed.rule, true)}
        </div>
      );
    }

    // Case 2: src|rule format
    if (parsed.type === 'srcRule') {
      const srcFieldName = extractFieldName(parsed.src);

      return (
        <div
          style={{
            display: 'table',
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '9px',
            backgroundColor: 'rgba(0,0,0,0.15)',
            borderRadius: '3px',
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          {renderRow('Src', srcFieldName)}
          {renderRow('Rule', parsed.rule, true)}
        </div>
      );
    }

    // Case 3: src only format
    if (parsed.type === 'srcOnly') {
      const srcFieldName = extractFieldName(parsed.src);

      return (
        <div
          style={{
            display: 'table',
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '9px',
            backgroundColor: 'rgba(0,0,0,0.15)',
            borderRadius: '3px',
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          {renderRow('Src', srcFieldName, true)}
        </div>
      );
    }

    // Case 4: direct rule format (e.g., "50>blue")
    if (parsed.type === 'directRule') {
      return <span style={{ fontSize: '10px', color: 'white' }}>{parsed.rule}</span>;
    }

    return <span style={{ fontSize: '10px', color: 'white' }}>{value}</span>;
  };

  return (
    <>
      {/* SECTION 1: Autocomplete Field Selector */}
      <div style={{ padding: '10px', borderBottom: '2px solid var(--dynamic-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)' }}>
            COLOUR RULES:
          </div>
          <Help
            onClick={(e) => setColorRuleHelpAnchorEl(e.currentTarget)}
            sx={{ cursor: 'pointer', fontSize: '18px', color: 'var(--blue-info)' }}
          />
          <Popover
            open={Boolean(colorRuleHelpAnchorEl)}
            anchorEl={colorRuleHelpAnchorEl}
            onClose={() => setColorRuleHelpAnchorEl(null)}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'left',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'left',
            }}
          >
            <Box sx={{ padding: '16px', maxWidth: '420px', backgroundColor: 'var(--dynamic-bg-light)' }}>
              <p style={{ margin: '0 0 12px 0', fontSize: '12px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                Color Rules Guide
              </p>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
                <p style={{ margin: '0 0 10px 0' }}>
                  <strong>Direct Rules:</strong> Apply color based on cell value<br />
                  <code style={{ backgroundColor: 'var(--dynamic-bg-medium)', padding: '2px 4px', borderRadius: '2px' }}>10>error</code>, <code style={{ backgroundColor: 'var(--dynamic-bg-medium)', padding: '2px 4px', borderRadius: '2px' }}>15%>red</code>
                </p>
                <p style={{ margin: '0 0 10px 0' }}>
                  <strong>Supported Colors:</strong> Hex colors (#FF0000) {'&'} semantic colors (info, error, critical, warning, debug)
                </p>
                <p style={{ margin: '0 0 10px 0' }}>
                  <strong>Operators:</strong> {'>'} | {'<'} | {'='} | {'>='} | {'<='}
                </p>
                <p style={{ margin: '0 0 10px 0' }}>
                  <strong>Percentage (Pct):</strong> Use when min/max sources defined. Rule applies to percentage of range between min and max.
                </p>
                <p style={{ margin: '0 0 10px 0' }}>
                  <strong>Application Order:</strong> Direct rule {'>'} Src|Custom rule {'>'} Src {'>'} Percentage
                </p>
                <p style={{ margin: '0' }}>
                  <strong>Note:</strong> Overrides replace schema rules. Edit a schema rule to convert it to an override. Rules will append in this order : if nothing is set in schema , then as a direct rule , if source is mentioned then as a custom rule , if min|max|rule is mentioned then it will override percentage rule.
                </p>
              </div>
            </Box>
          </Popover>
        </div>

        <Autocomplete
          size="small"
          options={availableFields}
          getOptionLabel={(option) => option.label}
          value={
            selectedFieldName
              ? availableFields.find((f) => f.key === selectedFieldName) || null
              : null
          }
          onChange={(_, newValue) => {
            if (newValue) {
              handleColorRuleFieldSelect(newValue.key);
            }
          }}
          onKeyDown={handleKeyDown}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Search or select field"
              placeholder="Start typing to search..."
            />
          )}
          sx={{ marginBottom: '8px' }}
          isOptionEqualToValue={(option, value) => option.key === value.key}
        />
      </div>

      {/* SECTION 2: Rule Editor */}
      {selectedFieldName && (
        <div style={{ padding: '12px', borderBottom: '2px solid var(--dynamic-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <p style={{ margin: '0', fontSize: '12px', fontWeight: 'bold' }}>EDIT RULE: {selectedFieldName}</p>
            <button
              onClick={() => setSelectedFieldName('')}
              style={{
                padding: '2px 8px',
                fontSize: '11px',
                backgroundColor: 'transparent',
                color: 'var(--text-secondary)',
                border: '1px solid var(--dynamic-border)',
                borderRadius: '3px',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              ✕
            </button>
          </div>
          <TextField
            label="Color Rule"
            size="small"
            fullWidth
            value={colorRuleInput}
            onChange={(e) => setColorRuleInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., 50>blue"
            margin="dense"
          />
          <TextField
            label="Background Color Rule"
            size="small"
            fullWidth
            value={backgroundColorRuleInput}
            onChange={(e) => setBackgroundColorRuleInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., -100<=red"
            margin="dense"
            style={{ marginTop: '8px' }}
          />
          <button
            onClick={handleApplyColorRule}
            style={{
              marginTop: '10px',
              padding: '8px 16px',
              width: '100%',
              backgroundColor: 'var(--blue-info)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
            }}
          >
            Apply Rule
          </button>
        </div>
      )}

      {/* SECTION 3: Applied Overrides & Schema Rules List */}
      <div style={{ padding: '12px', maxHeight: '200px', overflow: 'auto' }}>
        <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', marginBottom: '10px' }}>
          ACTIVE RULES:
        </div>
        {(() => {
          // Collect all fields with rules (both overrides and schema rules)
          const fieldsWithRules = new Map();

          // Add user overrides
          if (colorRules && colorRules.length > 0) {
            colorRules.forEach(rule => {
              if (!fieldsWithRules.has(rule.field_name)) {
                fieldsWithRules.set(rule.field_name, {});
              }
              fieldsWithRules.get(rule.field_name).override = rule;
            });
          }

          // Add schema rules from columns
          if (columns && columns.length > 0) {
            columns.forEach(col => {
              const fieldId = col.identifier || col.key;
              if (col.color || col.colorSrc || col.colorPercentage || col.backgroundColor || col.backgroundColorSrc || col.backgroundColorPercentage) {
                if (!fieldsWithRules.has(fieldId)) {
                  fieldsWithRules.set(fieldId, {});
                }
                const fieldData = fieldsWithRules.get(fieldId);
                fieldData.schemaColor = col.color;
                fieldData.schemaColorSrc = col.colorSrc;
                fieldData.schemaColorPercentage = col.colorPercentage;
                fieldData.schemaBackgroundColor = col.backgroundColor;
                fieldData.schemaBackgroundColorSrc = col.backgroundColorSrc;
                fieldData.schemaBackgroundColorPercentage = col.backgroundColorPercentage;
              }
            });
          }

          // Render all rules
          if (fieldsWithRules.size === 0) {
            return (
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0, textAlign: 'center', padding: '8px' }}>
                No rules configured
              </p>
            );
          }

          return Array.from(fieldsWithRules.entries()).map(([fieldName, data]) => (
            <div key={fieldName} style={{ marginBottom: '12px' }}>
              {/* User Override Card */}
              {data.override && (
                <div
                  style={{
                    padding: '10px 12px',
                    marginBottom: data.schemaColor || data.schemaColorSrc || data.schemaColorPercentage || data.schemaBackgroundColor || data.schemaBackgroundColorSrc || data.schemaBackgroundColorPercentage ? '8px' : '0',
                    backgroundColor: 'var(--blue-info)',
                    borderRadius: '6px',
                    border: '1px solid var(--blue-info)',
                    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div>
                      <p style={{ margin: '0', fontSize: '11px', fontWeight: 'bold', color: 'white' }}>
                        {fieldName}
                      </p>
                      <p style={{ margin: '2px 0 0 0', fontSize: '9px', color: 'rgba(255, 255, 255, 0.8)' }}>
                        Override
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => handleColorRuleFieldSelect(fieldName)}
                        style={{
                          padding: '4px 10px',
                          fontSize: '9px',
                          backgroundColor: 'rgba(255, 255, 255, 0.25)',
                          color: 'white',
                          border: '1px solid rgba(255, 255, 255, 0.5)',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontWeight: '600',
                          transition: 'all 0.2s',
                        }}
                        onMouseOver={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.35)')}
                        onMouseOut={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.25)')}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteColorRule(fieldName)}
                        style={{
                          padding: '4px 10px',
                          fontSize: '9px',
                          backgroundColor: 'rgba(255, 255, 255, 0.25)',
                          color: 'white',
                          border: '1px solid rgba(255, 255, 255, 0.5)',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontWeight: '600',
                          transition: 'all 0.2s',
                        }}
                        onMouseOver={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.35)')}
                        onMouseOut={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.25)')}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', color: 'white' }}>
                    {data.override.color_rule && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '9px', fontWeight: '600', minWidth: '70px', opacity: 0.9 }}>Text Color:</span>
                        <span style={{ fontSize: '10px', color: 'rgba(255, 255, 255, 0.95)' }}>{data.override.color_rule}</span>
                      </div>
                    )}
                    {data.override.background_color_rule && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '9px', fontWeight: '600', minWidth: '70px', opacity: 0.9 }}>BG Color:</span>
                        <span style={{ fontSize: '10px', color: 'rgba(255, 255, 255, 0.95)' }}>{data.override.background_color_rule}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Schema Rule Card (read-only) */}
              {(data.schemaColor || data.schemaColorSrc || data.schemaColorPercentage || data.schemaBackgroundColor || data.schemaBackgroundColorSrc || data.schemaBackgroundColorPercentage) && !data.override && (
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: '#a0826d',
                    borderRadius: '6px',
                    border: '1px solid #a0826d',
                    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div>
                      <p style={{ margin: '0', fontSize: '11px', fontWeight: 'bold', color: 'white' }}>
                        {fieldName}
                      </p>
                      <p style={{ margin: '2px 0 0 0', fontSize: '9px', color: 'rgba(255, 255, 255, 0.8)' }}>
                        Schema
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => handleColorRuleFieldSelect(fieldName)}
                        style={{
                          padding: '4px 10px',
                          fontSize: '9px',
                          backgroundColor: 'rgba(255, 255, 255, 0.25)',
                          color: 'white',
                          border: '1px solid rgba(255, 255, 255, 0.5)',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontWeight: '600',
                          transition: 'all 0.2s',
                        }}
                        onMouseOver={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.35)')}
                        onMouseOut={(e) => (e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.25)')}
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', color: 'white' }}>
                    {/* Text Color Section */}
                    {(data.schemaColor || data.schemaColorSrc || data.schemaColorPercentage) && (
                      <div>
                        <span style={{ fontSize: '9px', fontWeight: '600', opacity: 0.9, display: 'block', marginBottom: '4px' }}>Text Color:</span>
                        <div style={{ marginLeft: '0px' }}>
                          {data.schemaColor && <SmartRuleDisplay value={data.schemaColor} label="Rule" />}
                          {data.schemaColorSrc && (
                            <div style={{ marginTop: data.schemaColor ? '4px' : '0px' }}>
                              <SmartRuleDisplay value={data.schemaColorSrc} label="Src" />
                            </div>
                          )}
                          {data.schemaColorPercentage && (
                            <div style={{ marginTop: data.schemaColor || data.schemaColorSrc ? '4px' : '0px' }}>
                              <SmartRuleDisplay value={data.schemaColorPercentage} label="Pct" />
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Background Color Section */}
                    {(data.schemaBackgroundColor || data.schemaBackgroundColorSrc || data.schemaBackgroundColorPercentage) && (
                      <div style={{ marginTop: data.schemaColor || data.schemaColorSrc || data.schemaColorPercentage ? '4px' : '0px' }}>
                        <span style={{ fontSize: '9px', fontWeight: '600', opacity: 0.9, display: 'block', marginBottom: '4px' }}>BG Color:</span>
                        <div style={{ marginLeft: '0px' }}>
                          {data.schemaBackgroundColor && <SmartRuleDisplay value={data.schemaBackgroundColor} label="Rule" />}
                          {data.schemaBackgroundColorSrc && (
                            <div style={{ marginTop: data.schemaBackgroundColor ? '4px' : '0px' }}>
                              <SmartRuleDisplay value={data.schemaBackgroundColorSrc} label="Src" />
                            </div>
                          )}
                          {data.schemaBackgroundColorPercentage && (
                            <div style={{ marginTop: data.schemaBackgroundColor || data.schemaBackgroundColorSrc ? '4px' : '0px' }}>
                              <SmartRuleDisplay value={data.schemaBackgroundColorPercentage} label="Pct" />
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ));
        })()}
      </div>
    </>
  );
};

ColorRuleTab.propTypes = {
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      identifier: PropTypes.string,
      elaborateTitle: PropTypes.bool,
      sourceIndex: PropTypes.number,
      color: PropTypes.string,
      colorSrc: PropTypes.string,
      colorPercentage: PropTypes.string,
      backgroundColor: PropTypes.string,
      backgroundColorSrc: PropTypes.string,
      backgroundColorPercentage: PropTypes.string,
    })
  ),
  colorRules: PropTypes.arrayOf(
    PropTypes.shape({
      field_name: PropTypes.string.isRequired,
      color_rule: PropTypes.string,
      background_color_rule: PropTypes.string,
    })
  ),
  onColorRuleOverrideChange: PropTypes.func,
};

export default ColorRuleTab;