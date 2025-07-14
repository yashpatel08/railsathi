-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table: rail_sathi_complains
CREATE TABLE IF NOT EXISTS rail_sathi_complains (
    complain_id SERIAL PRIMARY KEY,
    pnr_number VARCHAR(10),
    is_pnr_validated VARCHAR(20) DEFAULT 'not-attempted',
    name VARCHAR(100),
    mobile_number VARCHAR(15),
    complain_type VARCHAR(50),
    complain_description TEXT,
    complain_date DATE,
    complain_status VARCHAR(20) DEFAULT 'pending',
    train_id INTEGER,
    train_number VARCHAR(10),
    train_name VARCHAR(100),
    train_no INTEGER,
    train_depot VARCHAR(10),
    coach VARCHAR(10),
    berth_no INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Table: rail_sathi_complain_media_files
CREATE TABLE IF NOT EXISTS rail_sathi_complain_media_files (
    id SERIAL PRIMARY KEY,
    complain_id INTEGER REFERENCES rail_sathi_complains(complain_id) ON DELETE CASCADE,
    media_type VARCHAR(50),
    media_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Table: trains (used for /trains endpoint)
CREATE TABLE IF NOT EXISTS trains (
    id SERIAL PRIMARY KEY,
    train_no VARCHAR(10) UNIQUE NOT NULL,
    train_name VARCHAR(100) NOT NULL,
    source VARCHAR(100),
    destination VARCHAR(100),
    start_time TIME,
    arrival_time TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for complaints
INSERT INTO rail_sathi_complains (
    pnr_number, name, mobile_number, complain_type, complain_description, 
    complain_date, train_number, train_name, coach, berth_no, created_by
) VALUES (
    '1234567890', 'yash patel', '+91-9876543210', 'Food Quality', 
    'Food was not fresh and tasted bad', CURRENT_DATE, 
    '12345', 'Rajdhani Express', 'A1', 23, 'patel yash'
) ON CONFLICT DO NOTHING;

-- Sample data for trains
INSERT INTO trains (train_no, train_name, source, destination, start_time, arrival_time)
VALUES
('12345', 'Rajdhani Express', 'Delhi', 'Mumbai', '07:00', '20:00')
ON CONFLICT DO NOTHING;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_complains_updated_at 
    BEFORE UPDATE ON rail_sathi_complains 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_media_updated_at 
    BEFORE UPDATE ON rail_sathi_complain_media_files 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trains_updated_at 
    BEFORE UPDATE ON trains
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_complain_mobile ON rail_sathi_complains(mobile_number);
CREATE INDEX IF NOT EXISTS idx_complain_date ON rail_sathi_complains(complain_date);
CREATE INDEX IF NOT EXISTS idx_complain_status ON rail_sathi_complains(complain_status);
CREATE INDEX IF NOT EXISTS idx_media_complain_id ON rail_sathi_complain_media_files(complain_id);
CREATE INDEX IF NOT EXISTS idx_train_no ON trains(train_no);
