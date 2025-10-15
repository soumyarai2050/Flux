import React from 'react';
import MenuItem from '@mui/material/MenuItem';

const MenuItemWrapper = (props) => {
  return <MenuItem {...props}>{props.children}</MenuItem>;
};

export default MenuItemWrapper; 