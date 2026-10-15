#include "BINIT.H"
#define CELL(r,c) ((unsigned char *)(0x3e9c+72*(r)+6*(c)))

/* ovl6:1D1A..1DDD exclusive; far cdecl, no arguments. */
void far initialize_top_setup(void)
{
    int row,col,bank,i;
    for(row=1;row<=4;++row)
        for(col=1;col<=10;++col) {
            CELL(row,col)[5]=1;
            CELL(row,col)[0]=1;
        }
    setup_driver_boundary();
    for(bank=0;bank<3;++bank)
        for(i=0;i<8;++i)
            *(int *)(0x55fd+128*bank+2*i)=11;
}

/* ovl6:1DDD..1F52 exclusive; far Pascal, low byte of argument tested.
 * A failed top placement restarts the entire padded-board initialization. */
void pascal far initialize_physical_board(int use_bottom_template)
{
    int row,col,retry;
    do {
        for(row=0;row<=11;++row)
            for(col=0;col<=11;++col) {
                unsigned char *cell=CELL(row,col);
                *(int *)(cell+2)=9;
                cell[5]=1;
                cell[0]=0;
                cell[4]=1;
            }
        initialize_top_setup();
        retry=0;
        for(row=1;row<=4 && !retry;++row)
            for(col=1;col<=10;++col)
                if(CELL(row,col)[5]!=0) {retry=1;break;}
    } while(retry);
    for(row=5;row<=6;++row)
        for(col=1;col<=10;++col)
            if(col==3 || col==4 || col==7 || col==8)
                CELL(row,col)[4]=0;
    if((unsigned char)use_bottom_template!=0) setup_template_boundary();
    for(row=7;row<=10;++row)
        for(col=1;col<=10;++col) {
            CELL(row,col)[0]=0;
            CELL(row,col)[4]=1;
            CELL(row,col)[5]=(unsigned char)use_bottom_template!=0 ? 0 : 1;
        }
}
