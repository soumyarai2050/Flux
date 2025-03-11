import { MenuItem as Item } from '@mui/material'
import styles from './MenuItem.module.css';

const MenuItem = ({ children, ...rest }) => {

    return (
        <Item className={styles.menu_item} {...rest}>
            {children}
        </Item >
    )
}

export default MenuItem;