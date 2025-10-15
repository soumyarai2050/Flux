import Item from '@mui/material/MenuItem';
import styles from './MenuItem.module.css';

const MenuItem = ({ children, ...rest }) => {

    return (
        <Item className={styles.menu_item} {...rest}>
            {children}
        </Item >
    )
}

export default MenuItem;