export default (sequelize, DataTypes) => {
  const EPICFlowsheet = sequelize.define('epic_flowsheet', {
    id: {
      type: DataTypes.BIGINT,
      autoIncrement: true,
      primaryKey: true,
    },
    idCase: {
      type: DataTypes.STRING,
    },
    idPatient: {
      type: DataTypes.BIGINT,
      allowNull: false,
    },
    FID: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    SSR: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    nih_admission: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    gcs_admission: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    bp_syst: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    bp_diast: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    ivt_start_date: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    ivt_start_time: {
      type: DataTypes.TIME,
      allowNull: true,
    },
    rtpa_dose: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    mca: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    aca: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    pca: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    vertebrobasilar: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    firstangio_result: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    prostheticvalves: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    stroke_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    tia_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    ich_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    hypertension: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    diabetes: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    hyperlipidemia: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    smoking: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    atrialfib: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    chd: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    lowoutput: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    pad: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    decompression: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    iat_stentintracran: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    iat_stentextracran: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    createdAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    updatedAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
  });
  
  EPICFlowsheet.associate = function (models) {
    // associations can be defined here
    EPICFlowsheet.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICFlowsheet;
};