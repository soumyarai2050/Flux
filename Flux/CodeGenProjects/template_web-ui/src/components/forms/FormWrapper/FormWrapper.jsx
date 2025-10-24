import React from 'react';
import TextFieldWrapper from '../TextFieldWrapper';
import DropdownWrapper from '../DropdownWrapper';
import AutocompleteWrapper from '../AutocompleteWrapper';
import CheckboxWrapper from '../CheckboxWrapper';
import DateTimeWrapper from '../DateTimeWrapper';
import NumericFieldWrapper from '../NumericFieldWrapper';
import MenuItemWrapper from '../MenuItemWrapper';
import { DATA_TYPES } from '../../../constants';


const FormWrapper = (props) => {
  const { type, customComponentType, autocomplete, numericFormat, numeric, menuItems, ...otherProps } = props;

  // Autocomplete
  if (customComponentType === 'autocomplete' || autocomplete) {
    return <AutocompleteWrapper {...otherProps} type={type} />;
  }

  // Numeric field
  if (
    type === DATA_TYPES.NUMBER && (numericFormat || numeric)
  ) {
    return <NumericFieldWrapper {...otherProps} type={type} decimalScale={numericFormat} />;
  }

  // Menu
  if (menuItems) {
    const items = menuItems || menu || [];
    return <MenuWrapper items={items} {...otherProps} />;
  }

  switch (type) {
    case DATA_TYPES.STRING:
      return <TextFieldWrapper {...otherProps} type={type} />;
    case DATA_TYPES.NUMBER:
      return <TextFieldWrapper {...otherProps} type={type} />;
    case DATA_TYPES.ENUM:
      return <DropdownWrapper {...otherProps} type={type} />;
    case DATA_TYPES.BOOLEAN:
      return <CheckboxWrapper {...otherProps} type={type} />;
    case DATA_TYPES.DATE_TIME:
      return <DateTimeWrapper {...otherProps} type={type} />;
    default:
      return <div>Unsupported input type: {type}</div>;
  }
};

export default FormWrapper; 