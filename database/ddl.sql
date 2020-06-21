create database reality;

create table reality.flats(
    title VARCHAR(300),
    price int,
    size int,
    meters int,
    price_per_meter DECIMAL(7,1),
    floor int,
    penb VARCHAR(1),
    state VARCHAR(50),
    link VARCHAR(300),
    primary key (title, price_per_meter)
);
